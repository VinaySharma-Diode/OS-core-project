"""
Disk Scheduling View for OS Core Simulator.
Visualizes disk scheduling algorithms and head movement.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QComboBox, QSpinBox, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QGraphicsView, QGraphicsScene, QGraphicsLineItem,
    QGraphicsEllipseItem, QGraphicsTextItem
)
from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QColor, QPen, QBrush, QFont

from core.scheduling import DiskScheduler, SchedulingAlgorithm, compare_algorithms

import random


class SchedulingView(QWidget):
    """
    Disk scheduling visualization with head movement animation.
    """
    
    def __init__(self):
        super().__init__()
        self.scheduler = DiskScheduler(total_tracks=200, initial_head=50)
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate_step)
        self.animation_steps = []
        self.current_step = 0
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Control panel
        controls = QHBoxLayout()
        
        # Algorithm selector
        controls.addWidget(QLabel("Algorithm:"))
        self.algo_combo = QComboBox()
        for algo in SchedulingAlgorithm:
            self.algo_combo.addItem(algo.value.upper(), algo)
        controls.addWidget(self.algo_combo)
        
        # Head position
        controls.addWidget(QLabel("Initial Head:"))
        self.head_spin = QSpinBox()
        self.head_spin.setRange(0, 199)
        self.head_spin.setValue(50)
        controls.addWidget(self.head_spin)
        
        # Request generator
        controls.addWidget(QLabel("Requests:"))
        self.req_spin = QSpinBox()
        self.req_spin.setRange(3, 20)
        self.req_spin.setValue(8)
        controls.addWidget(self.req_spin)
        
        btn_random = QPushButton("Generate Random")
        btn_random.clicked.connect(self.generate_requests)
        controls.addWidget(btn_random)
        
        btn_run = QPushButton("Run Algorithm")
        btn_run.clicked.connect(self.run_algorithm)
        controls.addWidget(btn_run)
        
        btn_reset = QPushButton("Reset")
        btn_reset.clicked.connect(self.reset_scheduler)
        controls.addWidget(btn_reset)
        
        layout.addLayout(controls)
        
        # Visualization area
        viz_group = QGroupBox("Disk Head Movement")
        viz_layout = QVBoxLayout()
        
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, 800, 200)
        
        self.view = QGraphicsView(self.scene)
        self.view.setMinimumHeight(250)
        self.view.setRenderHints(self.view.renderHints())
        viz_layout.addWidget(self.view)
        
        viz_group.setLayout(viz_layout)
        layout.addWidget(viz_group)
        
        # Request table
        self.request_table = QTableWidget()
        self.request_table.setColumnCount(3)
        self.request_table.setHorizontalHeaderLabels(["Request #", "Track", "Status"])
        self.request_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.request_table)
        
        # Statistics panel
        stats_layout = QHBoxLayout()
        
        self.stats_label = QLabel(
            "Algorithm: None\n"
            "Total Seek: 0 | Avg Seek: 0 | Requests: 0"
        )
        self.stats_label.setStyleSheet("font-family: monospace; padding: 10px;")
        stats_layout.addWidget(self.stats_label)
        
        # Comparison button
        btn_compare = QPushButton("Compare All Algorithms")
        btn_compare.clicked.connect(self.compare_algorithms)
        stats_layout.addWidget(btn_compare)
        
        layout.addLayout(stats_layout)
        
        self.setLayout(layout)
        
        # Initial draw
        self.draw_disk()
    
    def draw_disk(self):
        """Draw the disk visualization."""
        self.scene.clear()
        
        # Draw track line
        y = 100
        self.scene.addLine(50, y, 750, y, QPen(QColor("#888"), 2))
        
        # Draw track markers
        for i in range(0, 201, 20):
            x = 50 + (i / 200) * 700
            self.scene.addLine(x, y - 5, x, y + 5, QPen(QColor("#888"), 1))
            text = QGraphicsTextItem(str(i))
            text.setPos(x - 10, y + 10)
            text.setDefaultTextColor(QColor("#888"))
            self.scene.addItem(text)
        
        # Draw head position
        head_x = 50 + (self.scheduler.head_position / 200) * 700
        head = QGraphicsEllipseItem(head_x - 8, y - 8, 16, 16)
        head.setBrush(QBrush(QColor("#4CAF50")))
        self.scene.addItem(head)
        
        # Draw pending requests
        for i, request in enumerate(self.scheduler.request_queue):
            x = 50 + (request.track / 200) * 700
            circle = QGraphicsEllipseItem(x - 5, y - 20, 10, 10)
            circle.setBrush(QBrush(QColor("#FF9800")))
            self.scene.addItem(circle)
            
            text = QGraphicsTextItem(str(i + 1))
            text.setPos(x - 5, y - 35)
            text.setDefaultTextColor(QColor("#FF9800"))
            self.scene.addItem(text)
    
    def generate_requests(self):
        """Generate random disk requests."""
        self.scheduler.reset()
        self.scheduler.head_position = self.head_spin.value()
        
        count = self.req_spin.value()
        for _ in range(count):
            track = random.randint(0, 199)
            self.scheduler.add_request(track)
        
        self.update_request_table()
        self.draw_disk()
    
    def update_request_table(self):
        """Update the request table display."""
        self.request_table.setRowCount(len(self.scheduler.request_queue))
        
        for i, request in enumerate(self.scheduler.request_queue):
            self.request_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.request_table.setItem(i, 1, QTableWidgetItem(str(request.track)))
            status = "Pending"
            self.request_table.setItem(i, 2, QTableWidgetItem(status))
    
    def run_algorithm(self):
        """Run the selected scheduling algorithm."""
        if not self.scheduler.request_queue:
            self.generate_requests()
        
        algo = self.algo_combo.currentData()
        self.scheduler.set_algorithm(algo)
        
        # Get the schedule
        self.animation_steps = self.scheduler.schedule()
        self.current_step = 0
        
        # Start animation
        if self.animation_steps:
            self.timer.start(300)
        
        self.update_stats()
    
    def animate_step(self):
        """Animate one step of the disk head movement."""
        if self.current_step >= len(self.animation_steps):
            self.timer.stop()
            return
        
        track, seek_distance, wait_time = self.animation_steps[self.current_step]
        
        # Update head position
        self.scheduler.head_position = track
        
        # Redraw
        self.draw_disk()
        
        # Highlight current request
        y = 100
        x = 50 + (track / 200) * 700
        highlight = QGraphicsEllipseItem(x - 8, y - 28, 16, 16)
        highlight.setPen(QPen(QColor("#4CAF50"), 3))
        self.scene.addItem(highlight)
        
        self.current_step += 1
        self.update_stats()
    
    def update_stats(self):
        """Update statistics display."""
        stats = self.scheduler.get_statistics()
        
        self.stats_label.setText(
            f"Algorithm: {stats['algorithm'].upper()}\n"
            f"Total Seek: {stats['total_seek_time']} | "
            f"Avg Seek: {stats['avg_seek_time']:.1f} | "
            f"Requests: {stats['total_requests']}"
        )
    
    def compare_algorithms(self):
        """Compare all scheduling algorithms."""
        if not self.scheduler.request_queue:
            self.generate_requests()
        
        # Get request tracks
        tracks = [r.track for r in self.scheduler.request_queue]
        
        # Compare
        results = compare_algorithms(tracks, 200)
        
        # Display comparison
        comparison_text = "Algorithm Comparison:\n"
        comparison_text += "-" * 60 + "\n"
        comparison_text += f"{'Algorithm':<12} {'Total Seek':<12} {'Avg Seek':<12} {'Throughput':<12}\n"
        comparison_text += "-" * 60 + "\n"
        
        for algo, stats in results.items():
            comparison_text += (
                f"{algo.upper():<12} "
                f"{stats['total_seek_time']:<12} "
                f"{stats['avg_seek_time']:<12.1f} "
                f"{stats['throughput']:<12.2f}\n"
            )
        
        self.stats_label.setText(comparison_text)
    
    def reset_scheduler(self):
        """Reset the scheduler."""
        self.scheduler.reset()
        self.scheduler.head_position = self.head_spin.value()
        self.timer.stop()
        self.animation_steps = []
        self.current_step = 0
        
        self.request_table.setRowCount(0)
        self.stats_label.setText(
            "Algorithm: None\n"
            "Total Seek: 0 | Avg Seek: 0 | Requests: 0"
        )
        
        self.draw_disk()
