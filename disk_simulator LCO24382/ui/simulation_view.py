from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QGridLayout, QLabel, 
    QSlider, QHBoxLayout, QComboBox, QGroupBox, QTextEdit,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import QTimer, Qt
import random
from core.disk import Disk, AllocationMethod
from core.defragmentation import defragment_steps, defragment_basic, defragment_optimized
from core.cache import DiskCache, CachePolicy
from utils.report import export_csv, export_pdf


class SimulationView(QWidget):
    """
    Enhanced Disk simulation view with file system operations,
    allocation methods, cache management, and defragmentation.
    """

    def __init__(self):
        super().__init__()
        self.disk = Disk(size=64, block_size=4096)
        self.cache = DiskCache(capacity=16, policy=CachePolicy.LRU)
        
        self.layout = QVBoxLayout()
        
        # Create tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_disk_tab(), "Disk & Files")
        self.tabs.addTab(self.create_allocation_tab(), "Allocation Methods")
        self.tabs.addTab(self.create_cache_tab(), "Cache")
        self.tabs.addTab(self.create_defrag_tab(), "Defragmentation")
        
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

    def create_disk_tab(self):
        """Create disk operations tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Controls
        controls = QHBoxLayout()
        
        controls.addWidget(QLabel("Allocation Method:"))
        self.alloc_combo = QComboBox()
        for method in AllocationMethod:
            self.alloc_combo.addItem(method.value.title(), method)
        controls.addWidget(self.alloc_combo)
        
        btn_create = QPushButton("Create File")
        btn_create.clicked.connect(self.create_file)
        controls.addWidget(btn_create)
        
        btn_delete = QPushButton("Delete Random File")
        btn_delete.clicked.connect(self.delete_random_file)
        controls.addWidget(btn_delete)
        
        btn_mkdir = QPushButton("Create Directory")
        btn_mkdir.clicked.connect(self.create_directory)
        controls.addWidget(btn_mkdir)
        
        btn_reset = QPushButton("Reset Disk")
        btn_reset.clicked.connect(self.reset_disk)
        controls.addWidget(btn_reset)
        
        layout.addLayout(controls)
        
        # Disk grid
        self.disk_grid = QGridLayout()
        self.disk_labels = []
        
        for i in range(64):
            label = QLabel(f"{i}\n-")
            label.setStyleSheet("background-color: #333; color: #666; padding: 3px; font-size: 8px; border: 1px solid #555;")
            label.setAlignment(Qt.AlignCenter)
            label.setMinimumSize(50, 35)
            self.disk_labels.append(label)
            self.disk_grid.addWidget(label, i // 8, i % 8)
        
        layout.addLayout(self.disk_grid)
        
        # Current path and stats
        self.path_label = QLabel("Path: /")
        self.path_label.setStyleSheet("font-family: monospace; color: #4CAF50;")
        layout.addWidget(self.path_label)
        
        self.stats_label = QLabel(
            "Files: 0 | Free: 64/64 | IOPS: 0 | Avg Response: 0ms"
        )
        self.stats_label.setStyleSheet("font-family: monospace; color: #888;")
        layout.addWidget(self.stats_label)
        
        # File list
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(4)
        self.file_table.setHorizontalHeaderLabels(["Name", "Size", "Method", "Blocks"])
        self.file_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.file_table)
        
        # Export buttons
        export_layout = QHBoxLayout()
        btn_export_csv = QPushButton("Export CSV")
        btn_export_csv.clicked.connect(self.save_csv)
        export_layout.addWidget(btn_export_csv)
        
        btn_export_pdf = QPushButton("Export PDF")
        btn_export_pdf.clicked.connect(self.save_pdf)
        export_layout.addWidget(btn_export_pdf)
        
        layout.addLayout(export_layout)
        
        widget.setLayout(layout)
        return widget

    def create_allocation_tab(self):
        """Create allocation methods comparison tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        info = QTextEdit()
        info.setReadOnly(True)
        info.setMaximumHeight(150)
        info.setText(
            "File Allocation Methods:\n\n"
            "1. CONTIGUOUS - Blocks are allocated consecutively. Fast access but prone to fragmentation.\n"
            "2. LINKED - Blocks contain pointers to next block. No fragmentation but slower sequential access.\n"
            "3. INDEXED - An index block contains pointers to all data blocks. Fast direct access with some overhead."
        )
        layout.addWidget(info)
        
        # Comparison visualization will be shown here
        self.allocation_info = QLabel("Create files with different methods to compare")
        self.allocation_info.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(self.allocation_info)
        
        # Method statistics
        self.method_stats = QTableWidget()
        self.method_stats.setColumnCount(4)
        self.method_stats.setHorizontalHeaderLabels(["Method", "Files", "Avg Fragmentation", "Efficiency"])
        self.method_stats.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.method_stats)
        
        widget.setLayout(layout)
        return widget

    def create_cache_tab(self):
        """Create cache management tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Cache controls
        controls = QHBoxLayout()
        
        controls.addWidget(QLabel("Policy:"))
        self.cache_policy_combo = QComboBox()
        for policy in CachePolicy:
            self.cache_policy_combo.addItem(policy.value.upper(), policy)
        controls.addWidget(self.cache_policy_combo)
        
        btn_read = QPushButton("Read Block")
        btn_read.clicked.connect(self.read_cached_block)
        controls.addWidget(btn_read)
        
        btn_write = QPushButton("Write Block")
        btn_write.clicked.connect(self.write_cached_block)
        controls.addWidget(btn_write)
        
        btn_flush = QPushButton("Flush Cache")
        btn_flush.clicked.connect(self.flush_cache)
        controls.addWidget(btn_flush)
        
        layout.addLayout(controls)
        
        # Cache visualization
        self.cache_grid = QGridLayout()
        self.cache_labels = []
        
        for i in range(16):
            label = QLabel(f"Slot {i}\nEmpty")
            label.setStyleSheet("background-color: #333; color: #666; padding: 5px; border: 1px solid #555;")
            label.setAlignment(Qt.AlignCenter)
            self.cache_labels.append(label)
            self.cache_grid.addWidget(label, i // 4, i % 4)
        
        layout.addLayout(self.cache_grid)
        
        # Cache stats
        self.cache_stats_label = QLabel(
            "Hit Rate: 0% | Hits: 0 | Misses: 0 | Evictions: 0"
        )
        self.cache_stats_label.setStyleSheet("font-family: monospace; padding: 10px;")
        layout.addWidget(self.cache_stats_label)
        
        widget.setLayout(layout)
        return widget

    def create_defrag_tab(self):
        """Create defragmentation tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Defrag controls
        controls = QHBoxLayout()
        
        btn_defrag_basic = QPushButton("Basic Defragment")
        btn_defrag_basic.clicked.connect(self.run_basic_defrag)
        controls.addWidget(btn_defrag_basic)
        
        btn_defrag_opt = QPushButton("Optimized Defragment")
        btn_defrag_opt.clicked.connect(self.run_optimized_defrag)
        controls.addWidget(btn_defrag_opt)
        
        btn_defrag_anim = QPushButton("Animated Defragment")
        btn_defrag_anim.clicked.connect(self.run_animated_defrag)
        controls.addWidget(btn_defrag_anim)
        
        # Speed slider
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(50, 500)
        self.speed_slider.setValue(200)
        self.speed_slider.setTickInterval(50)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        controls.addWidget(QLabel("Speed:"))
        controls.addWidget(self.speed_slider)
        
        layout.addLayout(controls)
        
        # Fragmentation info
        self.frag_info = QTextEdit()
        self.frag_info.setReadOnly(True)
        self.frag_info.setMaximumHeight(100)
        layout.addWidget(self.frag_info)
        
        widget.setLayout(layout)
        return widget

    # Disk operations
    def create_file(self):
        """Create a new file."""
        method = self.alloc_combo.currentData()
        name = f"File{len(self.disk.files) + 1}"
        size = random.randint(2, 8)
        
        try:
            self.disk.create_file(name, size, method)
            # Simulate cache interaction
            for block in self.disk.get_file_blocks(name):
                self.cache.put(block, f"data_{name}".encode())
        except ValueError as e:
            self.stats_label.setText(f"Error: {str(e)}")
        
        self.update_disk_display()

    def delete_random_file(self):
        """Delete a random file."""
        if self.disk.files:
            name = random.choice(list(self.disk.files.keys()))
            self.disk.delete_file(name)
            self.update_disk_display()

    def create_directory(self):
        """Create a new directory."""
        name = f"Dir{len(self.disk.current_dir.subdirectories) + 1}"
        try:
            self.disk.mkdir(name)
            self.path_label.setText(f"Path: {self.disk.pwd()}")
        except ValueError:
            pass

    def reset_disk(self):
        """Reset the disk."""
        self.disk.reset()
        self.cache.reset()
        self.update_disk_display()

    # Cache operations
    def read_cached_block(self):
        """Read a block from cache."""
        block = random.randint(0, self.disk.size - 1)
        data = self.cache.get(block)
        self.update_cache_display()

    def write_cached_block(self):
        """Write to a cached block."""
        block = random.randint(0, self.disk.size - 1)
        self.cache.put(block, f"data_{block}".encode(), dirty=True)
        self.update_cache_display()

    def flush_cache(self):
        """Flush cache to disk."""
        self.cache.flush()
        self.update_cache_display()

    # Defragmentation
    def run_basic_defrag(self):
        """Run basic defragmentation."""
        defragment_basic(self.disk)
        self.update_disk_display()
        self.update_frag_info()

    def run_optimized_defrag(self):
        """Run optimized defragmentation."""
        defragment_optimized(self.disk)
        self.update_disk_display()
        self.update_frag_info()

    def run_animated_defrag(self):
        """Run animated defragmentation."""
        self.defrag_steps = list(defragment_steps(self.disk))
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate_defrag_step)
        self.timer.start(self.speed_slider.value())

    def animate_defrag_step(self):
        """Animate one defragmentation step."""
        if not self.defrag_steps:
            self.timer.stop()
            return
        
        old, new, name = self.defrag_steps.pop(0)
        self.disk.blocks[old] = None
        if self.disk.blocks[new] is None:
            from core.disk import DiskBlock
            self.disk.blocks[new] = DiskBlock(data=name)
        self.update_disk_display()

    # Update methods
    def update_disk_display(self):
        """Update the disk grid display."""
        from core.fragmentation import fragmentation_level, get_fragmentation_report
        
        colors = {
            AllocationMethod.CONTIGUOUS: "#2196F3",  # Blue
            AllocationMethod.LINKED: "#4CAF50",      # Green
            AllocationMethod.INDEXED: "#FF9800"     # Orange
        }
        
        for i, block in enumerate(self.disk.blocks):
            label = self.disk_labels[i]
            
            if block is None:
                label.setText(f"{i}\n-")
                label.setStyleSheet("background-color: #333; color: #666; padding: 3px; font-size: 8px; border: 1px solid #555;")
            else:
                # Get file info
                file_name = block.data
                if file_name and file_name in self.disk.files:
                    method = self.disk.files[file_name].allocation_method
                    color = colors.get(method, "#666")
                    label.setText(f"{i}\n{file_name}")
                    label.setStyleSheet(f"background-color: {color}; color: white; padding: 3px; font-size: 8px; border: 1px solid #fff;")
                else:
                    label.setText(f"{i}\n?")
                    label.setStyleSheet("background-color: #666; color: white; padding: 3px; font-size: 8px;")
        
        # Update stats
        stats = self.disk.get_stats()
        frag_report = get_fragmentation_report(self.disk)
        
        self.stats_label.setText(
            f"Files: {stats['file_count']} | "
            f"Free: {stats['free_blocks']}/{stats['total_blocks']} | "
            f"Fragmentation: {frag_report['internal_fragmentation']:.1f}%"
        )
        
        # Update file table
        self.file_table.setRowCount(len(self.disk.files))
        for row, (name, metadata) in enumerate(self.disk.files.items()):
            self.file_table.setItem(row, 0, QTableWidgetItem(name))
            self.file_table.setItem(row, 1, QTableWidgetItem(str(metadata.size)))
            self.file_table.setItem(row, 2, QTableWidgetItem(metadata.allocation_method.value))
            blocks = self.disk.get_file_blocks(name)
            self.file_table.setItem(row, 3, QTableWidgetItem(str(len(blocks))))
        
        # Update method stats
        method_stats = frag_report['allocation_stats']
        self.method_stats.setRowCount(3)
        for row, (method, stats) in enumerate(method_stats.items()):
            self.method_stats.setItem(row, 0, QTableWidgetItem(method.value.title()))
            self.method_stats.setItem(row, 1, QTableWidgetItem(str(stats['count'])))
            self.method_stats.setItem(row, 2, QTableWidgetItem(f"{stats['percentage']:.1f}%"))
            self.method_stats.setItem(row, 3, QTableWidgetItem("N/A"))
        
        self.path_label.setText(f"Path: {self.disk.pwd()}")

    def update_cache_display(self):
        """Update cache visualization."""
        cache_contents = self.cache.get_cache_contents()
        stats = self.cache.get_stats()
        
        for i, label in enumerate(self.cache_labels):
            if i < len(cache_contents):
                entry = cache_contents[i]
                block_id = entry['block_id']
                dirty = "D" if entry['dirty'] else ""
                label.setText(f"Slot {i}\nBlock {block_id}{dirty}")
                
                color = "#4CAF50" if not entry['dirty'] else "#FF9800"
                label.setStyleSheet(f"background-color: {color}; color: white; padding: 5px; border: 1px solid #fff;")
            else:
                label.setText(f"Slot {i}\nEmpty")
                label.setStyleSheet("background-color: #333; color: #666; padding: 5px; border: 1px solid #555;")
        
        self.cache_stats_label.setText(
            f"Hit Rate: {stats['hit_rate']:.1%} | "
            f"Hits: {stats['hits']} | "
            f"Misses: {stats['misses']} | "
            f"Evictions: {stats['evictions']}"
        )

    def update_frag_info(self):
        """Update fragmentation information."""
        from core.fragmentation import get_fragmentation_report
        from core.performance import calculate_metrics
        
        frag_report = get_fragmentation_report(self.disk)
        metrics = calculate_metrics(self.disk)
        
        self.frag_info.setText(
            f"Fragmentation Analysis:\n"
            f"Internal Fragmentation: {frag_report['internal_fragmentation']:.2f}%\n"
            f"External Fragmentation: {frag_report['external_fragmentation']:.2f}%\n"
            f"Seek Time: {metrics['seek_time']} | "
            f"Efficiency: {metrics['efficiency']:.2f}%"
        )

    def save_csv(self):
        """Export to CSV."""
        export_csv(self.disk, "disk_report.csv")

    def save_pdf(self):
        """Export to PDF."""
        export_pdf(self.disk, "disk_report.pdf")
