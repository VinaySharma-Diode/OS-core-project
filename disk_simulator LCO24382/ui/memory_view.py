"""
Memory Management View for OS Core Simulator.
Visualizes paging, virtual memory, and page replacement.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QGridLayout, QComboBox, QSpinBox, QGroupBox,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from core.memory import MemoryManager, PageReplacementAlgorithm
from core.process import ProcessScheduler, ProcessType

import random


class MemoryView(QWidget):
    """
    Memory management visualization with paging and virtual memory.
    """
    
    def __init__(self):
        super().__init__()
        self.memory = MemoryManager(
            physical_memory_size=32,
            virtual_memory_size=128,
            replacement_algorithm=PageReplacementAlgorithm.LRU
        )
        
        self.init_ui()
        self.update_display()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Control panel
        controls = QHBoxLayout()
        
        # Algorithm selector
        controls.addWidget(QLabel("Algorithm:"))
        self.algo_combo = QComboBox()
        for algo in PageReplacementAlgorithm:
            self.algo_combo.addItem(algo.value.upper(), algo)
        self.algo_combo.currentIndexChanged.connect(self.change_algorithm)
        controls.addWidget(self.algo_combo)
        
        # Process creator
        controls.addWidget(QLabel("Process ID:"))
        self.pid_spin = QSpinBox()
        self.pid_spin.setRange(1, 10)
        controls.addWidget(self.pid_spin)
        
        btn_create = QPushButton("Create Process")
        btn_create.clicked.connect(self.create_process)
        controls.addWidget(btn_create)
        
        btn_access = QPushButton("Random Access")
        btn_access.clicked.connect(self.random_access)
        controls.addWidget(btn_access)
        
        btn_reset = QPushButton("Reset")
        btn_reset.clicked.connect(self.reset_memory)
        controls.addWidget(btn_reset)
        
        layout.addLayout(controls)
        
        # Physical memory visualization
        phys_group = QGroupBox("Physical Memory (Frames)")
        phys_layout = QGridLayout()
        self.frame_labels = []
        
        for i in range(32):
            label = QLabel(f"Frame {i}\nEmpty")
            label.setStyleSheet("background-color: #333; color: white; padding: 5px; border: 1px solid #555;")
            label.setAlignment(Qt.AlignCenter)
            label.setMinimumSize(80, 40)
            self.frame_labels.append(label)
            phys_layout.addWidget(label, i // 8, i % 8)
        
        phys_group.setLayout(phys_layout)
        layout.addWidget(phys_group)
        
        # Statistics panel
        stats_layout = QHBoxLayout()
        
        # TLB Stats
        tlb_group = QGroupBox("TLB Statistics")
        tlb_layout = QVBoxLayout()
        self.tlb_label = QLabel("Hit Rate: 0%\nEntries: 0/16")
        tlb_layout.addWidget(self.tlb_label)
        tlb_group.setLayout(tlb_layout)
        stats_layout.addWidget(tlb_group)
        
        # Page Fault Stats
        fault_group = QGroupBox("Page Faults")
        fault_layout = QVBoxLayout()
        self.fault_label = QLabel("Faults: 0\nHits: 0\nRate: 0%")
        fault_layout.addWidget(self.fault_label)
        fault_group.setLayout(fault_layout)
        stats_layout.addWidget(fault_group)
        
        # Memory Stats
        mem_group = QGroupBox("Memory Usage")
        mem_layout = QVBoxLayout()
        self.mem_label = QLabel("Used: 0/32\nFree: 32")
        mem_layout.addWidget(self.mem_label)
        mem_group.setLayout(mem_layout)
        stats_layout.addWidget(mem_group)
        
        layout.addLayout(stats_layout)
        
        # Process table
        self.process_table = QTableWidget()
        self.process_table.setColumnCount(3)
        self.process_table.setHorizontalHeaderLabels(["Process ID", "Pages", "Status"])
        self.process_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.process_table)
        
        self.setLayout(layout)
    
    def change_algorithm(self, index):
        """Change page replacement algorithm."""
        algo = self.algo_combo.currentData()
        self.memory.replacement_algorithm = algo
    
    def create_process(self):
        """Create a new process."""
        pid = self.pid_spin.value()
        if pid not in self.memory.page_tables:
            self.memory.create_page_table(pid)
            
            # Allocate some pages
            for page in random.sample(range(self.memory.virtual_memory_size), 5):
                self.memory.access_page(pid, page)
        
        self.update_display()
    
    def random_access(self):
        """Simulate random memory access."""
        for pid in list(self.memory.page_tables.keys()):
            page = random.randint(0, self.memory.virtual_memory_size - 1)
            self.memory.access_page(pid, page)
        
        self.update_display()
    
    def reset_memory(self):
        """Reset memory manager."""
        self.memory.reset()
        self.update_display()
    
    def update_display(self):
        """Update the memory visualization."""
        # Update frame labels
        memory_map = self.memory.get_memory_map()
        colors = ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0", "#F44336", "#00BCD4", "#8BC34A", "#FFEB3B", "#795548", "#607D8B"]
        
        for i, frame_data in enumerate(memory_map):
            label = self.frame_labels[i]
            
            if frame_data is None:
                label.setText(f"Frame {i}\nEmpty")
                label.setStyleSheet("background-color: #333; color: #666; padding: 5px; border: 1px solid #555;")
            else:
                pid = frame_data["process"]
                page = frame_data["page"]
                color = colors[pid % len(colors)] if pid else "#666"
                dirty = "D" if frame_data["modified"] else ""
                ref = "R" if frame_data["referenced"] else ""
                
                label.setText(f"P{pid}:Page{page}\n{ref}{dirty}")
                label.setStyleSheet(f"background-color: {color}; color: white; padding: 5px; border: 1px solid #fff;")
        
        # Update statistics
        stats = self.memory.get_stats()
        tlb_stats = stats["tlb_stats"]
        
        self.tlb_label.setText(
            f"Hit Rate: {tlb_stats['hit_rate']:.1%}\n"
            f"Entries: {tlb_stats['entries_used']}/{tlb_stats['size']}"
        )
        
        self.fault_label.setText(
            f"Faults: {stats['page_faults']}\n"
            f"Hits: {stats['page_hits']}\n"
            f"Rate: {stats['page_fault_rate']:.1%}"
        )
        
        self.mem_label.setText(
            f"Used: {stats['used_frames']}/{stats['physical_frames']}\n"
            f"Free: {stats['free_frames']}"
        )
        
        # Update process table
        self.process_table.setRowCount(len(self.memory.page_tables))
        for row, (pid, table) in enumerate(self.memory.page_tables.items()):
            self.process_table.setItem(row, 0, QTableWidgetItem(str(pid)))
            self.process_table.setItem(row, 1, QTableWidgetItem(str(len(table))))
            self.process_table.setItem(row, 2, QTableWidgetItem("Active"))
