"""
RAID Array Visualization View for OS Core Simulator.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QSpinBox, QTableWidget,
    QTableWidgetItem, QGroupBox, QGridLayout, QSplitter,
    QHeaderView, QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
import numpy as np

from core.raid import RAIDArray, RAIDLevel, DiskDrive


class DiskVisualizationWidget(QWidget):
    """Widget for visualizing RAID disk array."""
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(600, 300)
        self.raid = None
        self.selected_disk = None
        
    def set_raid(self, raid: RAIDArray):
        """Set RAID array to visualize."""
        self.raid = raid
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor('#2d2d2d'))
        
        if not self.raid:
            painter.setPen(QColor('white'))
            painter.setFont(QFont('Arial', 14))
            painter.drawText(self.rect(), Qt.AlignCenter, "No RAID array configured")
            return
            
        # Draw disks
        disk_width = 80
        disk_height = 120
        spacing = 20
        margin = 40
        
        # Calculate layout
        total_width = self.raid.num_disks * disk_width + (self.raid.num_disks - 1) * spacing + 2 * margin
        start_x = (self.width() - total_width) // 2 + margin
        start_y = (self.height() - disk_height) // 2
        
        for i, disk in enumerate(self.raid.disks):
            x = start_x + i * (disk_width + spacing)
            y = start_y
            
            # Disk background
            if disk.failed:
                color = QColor('#f44336')  # Red for failed
            elif disk.disk_id == self.selected_disk:
                color = QColor('#ff9800')  # Orange for selected
            else:
                color = QColor('#4caf50')  # Green for healthy
                
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor('white'), 2))
            painter.drawRoundedRect(x, y, disk_width, disk_height, 8, 8)
            
            # Disk label
            painter.setPen(QColor('white'))
            painter.setFont(QFont('Arial', 10, QFont.Bold))
            painter.drawText(x, y - 5, disk_width, 20, Qt.AlignCenter, f"Disk {i}")
            
            # Disk info
            painter.setFont(QFont('Arial', 8))
            
            # Usage bar
            used_blocks = sum(1 for b in disk.blocks if b is not None)
            usage_pct = (used_blocks / disk.size) * 100
            
            bar_height = 8
            bar_y = y + 30
            painter.setBrush(QBrush(QColor('#555')))
            painter.drawRect(x + 5, bar_y, disk_width - 10, bar_height)
            
            fill_width = int((disk_width - 10) * usage_pct / 100)
            painter.setBrush(QBrush(QColor('#2196f3')))
            painter.drawRect(x + 5, bar_y, fill_width, bar_height)
            
            # Info text
            info_y = bar_y + 25
            painter.drawText(x + 5, info_y, f"{usage_pct:.0f}%")
            painter.drawText(x + 5, info_y + 15, f"{used_blocks}/{disk.size}")
            
            if disk.failed:
                painter.setPen(QColor('#f44336'))
                painter.setFont(QFont('Arial', 10, QFont.Bold))
                painter.drawText(x + 5, y + disk_height - 15, "FAILED")
            else:
                painter.setPen(QColor('#4caf50'))
                painter.drawText(x + 5, y + disk_height - 15, "OK")
                
        # Draw RAID level indicator
        painter.setPen(QColor('white'))
        painter.setFont(QFont('Arial', 12, QFont.Bold))
        level_text = f"RAID {self.raid.level.value.replace('RAID_', '')}"
        painter.drawText(self.rect(), Qt.AlignTop | Qt.AlignHCenter, level_text)
        
        # Draw capacity info
        painter.setFont(QFont('Arial', 10))
        cap_text = f"Usable: {self.raid.usable_capacity} | Total: {self.raid.disk_size * self.raid.num_disks}"
        painter.drawText(self.rect(), Qt.AlignBottom | Qt.AlignHCenter, cap_text)
        
        painter.end()
        
    def mousePressEvent(self, event):
        """Handle mouse click to select disk."""
        if not self.raid:
            return
            
        # Calculate which disk was clicked
        disk_width = 80
        spacing = 20
        margin = 40
        
        total_width = self.raid.num_disks * disk_width + (self.raid.num_disks - 1) * spacing + 2 * margin
        start_x = (self.width() - total_width) // 2 + margin
        
        x = event.x()
        relative_x = x - start_x
        
        disk_index = int(relative_x / (disk_width + spacing))
        if 0 <= disk_index < self.raid.num_disks:
            self.selected_disk = disk_index
            self.update()


class RAIDView(QWidget):
    """
    RAID array management and visualization view.
    """
    
    def __init__(self):
        super().__init__()
        
        self.raid = None
        self.init_ui()
        self.create_raid()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Top controls
        controls_layout = QHBoxLayout()
        
        # RAID level selector
        controls_layout.addWidget(QLabel("RAID Level:"))
        self.combo_raid_level = QComboBox()
        for level in RAIDLevel:
            self.combo_raid_level.addItem(level.value.upper(), level)
        self.combo_raid_level.currentIndexChanged.connect(self.create_raid)
        controls_layout.addWidget(self.combo_raid_level)
        
        # Disk count
        controls_layout.addWidget(QLabel("Disks:"))
        self.spin_disks = QSpinBox()
        self.spin_disks.setRange(2, 8)
        self.spin_disks.setValue(4)
        self.spin_disks.valueChanged.connect(self.create_raid)
        controls_layout.addWidget(self.spin_disks)
        
        # Disk size
        controls_layout.addWidget(QLabel("Disk Size:"))
        self.spin_size = QSpinBox()
        self.spin_size.setRange(50, 500)
        self.spin_size.setValue(100)
        self.spin_size.setSuffix(" blocks")
        self.spin_size.valueChanged.connect(self.create_raid)
        controls_layout.addWidget(self.spin_size)
        
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Main splitter
        splitter = QSplitter(Qt.Vertical)
        
        # Visualization
        self.disk_widget = DiskVisualizationWidget()
        splitter.addWidget(self.disk_widget)
        
        # Statistics and controls
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout()
        
        # Status group
        status_group = QGroupBox("Array Status")
        status_layout = QVBoxLayout()
        
        self.lbl_status = QLabel("Healthy")
        self.lbl_status.setStyleSheet("color: #4caf50; font-size: 16px; font-weight: bold;")
        status_layout.addWidget(self.lbl_status)
        
        # Progress bar for rebuild
        self.progress_rebuild = QProgressBar()
        self.progress_rebuild.setVisible(False)
        status_layout.addWidget(QLabel("Rebuild Progress:"))
        status_layout.addWidget(self.progress_rebuild)
        
        # Stats grid
        stats_grid = QGridLayout()
        
        self.lbl_total = QLabel("-")
        self.lbl_usable = QLabel("-")
        self.lbl_redundancy = QLabel("-")
        self.lbl_reads = QLabel("0")
        self.lbl_writes = QLabel("0")
        
        stats_grid.addWidget(QLabel("Total Capacity:"), 0, 0)
        stats_grid.addWidget(self.lbl_total, 0, 1)
        stats_grid.addWidget(QLabel("Usable Capacity:"), 1, 0)
        stats_grid.addWidget(self.lbl_usable, 1, 1)
        stats_grid.addWidget(QLabel("Redundancy:"), 2, 0)
        stats_grid.addWidget(self.lbl_redundancy, 2, 1)
        stats_grid.addWidget(QLabel("Read Ops:"), 3, 0)
        stats_grid.addWidget(self.lbl_reads, 3, 1)
        stats_grid.addWidget(QLabel("Write Ops:"), 4, 0)
        stats_grid.addWidget(self.lbl_writes, 4, 1)
        
        status_layout.addLayout(stats_grid)
        status_group.setLayout(status_layout)
        bottom_layout.addWidget(status_group)
        
        # Actions group
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout()
        
        btn_fail = QPushButton("💥 Fail Selected Disk")
        btn_fail.setStyleSheet("background-color: #f44336; color: white;")
        btn_fail.clicked.connect(self.fail_disk)
        actions_layout.addWidget(btn_fail)
        
        btn_rebuild = QPushButton("🔧 Rebuild Disk")
        btn_rebuild.setStyleSheet("background-color: #4caf50; color: white;")
        btn_rebuild.clicked.connect(self.rebuild_disk)
        actions_layout.addWidget(btn_rebuild)
        
        btn_write = QPushButton("📝 Write Data")
        btn_write.clicked.connect(self.write_data)
        actions_layout.addWidget(btn_write)
        
        btn_read = QPushButton("📖 Read Data")
        btn_read.clicked.connect(self.read_data)
        actions_layout.addWidget(btn_read)
        
        actions_layout.addStretch()
        actions_group.setLayout(actions_layout)
        bottom_layout.addWidget(actions_group)
        
        # Disk details table
        details_group = QGroupBox("Disk Details")
        details_layout = QVBoxLayout()
        
        self.disk_table = QTableWidget()
        self.disk_table.setColumnCount(4)
        self.disk_table.setHorizontalHeaderLabels(["Disk", "Status", "Used %", "Operations"])
        self.disk_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        details_layout.addWidget(self.disk_table)
        
        details_group.setLayout(details_layout)
        bottom_layout.addWidget(details_group)
        
        bottom_widget.setLayout(bottom_layout)
        splitter.addWidget(bottom_widget)
        
        splitter.setSizes([350, 250])
        layout.addWidget(splitter)
        
        self.setLayout(layout)
        
        # Update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(1000)
        
    def create_raid(self):
        """Create new RAID array."""
        level = self.combo_raid_level.currentData()
        num_disks = self.spin_disks.value()
        disk_size = self.spin_size.value()
        
        self.raid = RAIDArray(level, disk_size, num_disks)
        self.disk_widget.set_raid(self.raid)
        self.update_display()
        
    def update_display(self):
        """Update all display elements."""
        if not self.raid:
            return
            
        status = self.raid.get_status()
        
        # Update status label
        if status['failed_disks']:
            self.lbl_status.setText("DEGRADED")
            self.lbl_status.setStyleSheet("color: #ff9800;")
        else:
            self.lbl_status.setText("HEALTHY")
            self.lbl_status.setStyleSheet("color: #4caf50;")
            
        # Update stats
        self.lbl_total.setText(f"{status['num_disks'] * status['disk_size']} blocks")
        self.lbl_usable.setText(f"{status['usable_capacity']} blocks")
        self.lbl_redundancy.setText(f"{status['redundancy_disks']} disk(s)")
        self.lbl_reads.setText(str(status['read_operations']))
        self.lbl_writes.setText(str(status['write_operations']))
        
        # Update disk table
        self.disk_table.setRowCount(self.raid.num_disks)
        
        for i, disk in enumerate(self.raid.disks):
            used = sum(1 for b in disk.blocks if b is not None)
            usage = (used / disk.size) * 100
            
            self.disk_table.setItem(i, 0, QTableWidgetItem(f"Disk {i}"))
            
            status_item = QTableWidgetItem("FAILED" if disk.failed else "OK")
            if disk.failed:
                status_item.setBackground(QColor('#f44336'))
                status_item.setForeground(QColor('white'))
            else:
                status_item.setBackground(QColor('#4caf50'))
                status_item.setForeground(QColor('white'))
            self.disk_table.setItem(i, 1, status_item)
            
            self.disk_table.setItem(i, 2, QTableWidgetItem(f"{usage:.1f}%"))
            self.disk_table.setItem(i, 3, QTableWidgetItem("-"))
            
        self.disk_widget.update()
        
    def fail_disk(self):
        """Simulate disk failure."""
        if not self.raid:
            return
            
        selected = self.disk_widget.selected_disk
        if selected is None:
            QMessageBox.warning(self, "No Selection", "Please select a disk first")
            return
            
        if self.raid.fail_disk(selected):
            QMessageBox.information(self, "Disk Failed", f"Disk {selected} has been marked as failed")
            self.update_display()
        else:
            QMessageBox.critical(self, "Error", "Failed to fail disk")
            
    def rebuild_disk(self):
        """Rebuild failed disk."""
        if not self.raid:
            return
            
        # Find failed disk
        failed = [i for i, d in enumerate(self.raid.disks) if d.failed]
        
        if not failed:
            QMessageBox.information(self, "No Failed Disks", "No failed disks to rebuild")
            return
            
        # Rebuild first failed disk
        disk_id = failed[0]
        
        if self.raid.rebuild_disk(disk_id):
            QMessageBox.information(self, "Rebuild Complete", f"Disk {disk_id} has been rebuilt")
            self.update_display()
        else:
            QMessageBox.critical(self, "Error", "Rebuild failed")
            
    def write_data(self):
        """Simulate writing data to RAID array."""
        if not self.raid:
            return
            
        import random
        block = random.randint(0, self.raid.usable_capacity - 1)
        data = b"X" * 512
        
        if self.raid.write(block, data):
            QMessageBox.information(self, "Write Complete", f"Data written to block {block}")
            self.update_display()
        else:
            QMessageBox.critical(self, "Error", "Write failed")
            
    def read_data(self):
        """Simulate reading data from RAID array."""
        if not self.raid:
            return
            
        import random
        block = random.randint(0, self.raid.usable_capacity - 1)
        
        data = self.raid.read(block)
        if data is not None:
            QMessageBox.information(self, "Read Complete", f"Data read from block {block}")
        else:
            QMessageBox.critical(self, "Error", "Read failed - block may be corrupted")
