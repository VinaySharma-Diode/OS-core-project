"""
Deadlock Detection and Visualization View for OS Core Simulator.
"""

from typing import List
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QTableWidget,
    QTableWidgetItem, QTextEdit, QGroupBox, QGridLayout,
    QHeaderView, QSplitter, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QBrush
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np

from core.deadlock import (
    DeadlockDetector, BankersAlgorithm, ResourceAllocationGraph,
    ResourceType
)
from core.process import ProcessScheduler


class ResourceGraphWidget(QWidget):
    """Custom widget for drawing resource allocation graph."""
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 300)
        self.rag = ResourceAllocationGraph()
        self.deadlocked_processes = []
        
    def set_graph(self, rag: ResourceAllocationGraph, deadlocked: List[int] = None):
        """Update graph data."""
        self.rag = rag
        self.deadlocked_processes = deadlocked or []
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Clear background
        painter.fillRect(self.rect(), QColor('#2d2d2d'))
        
        if not self.rag.processes:
            painter.setPen(QColor('white'))
        painter.setFont(QFont('Arial', 12))
        painter.drawText(self.rect(), Qt.AlignCenter, "No processes/resources")
        return
        
        # Calculate positions
        center_x = width // 2
        center_y = height // 2
        radius = min(width, height) // 3
        
        process_list = list(self.rag.processes)
        n = len(process_list)
        
        # Draw processes (circles on left)
        process_positions = {}
        for i, pid in enumerate(process_list):
            angle = 2 * 3.14159 * i / n - 3.14159 / 2
            x = center_x - radius // 2 + int(radius * 0.3 * np.cos(angle))
            y = center_y + int(radius * 0.5 * np.sin(angle))
            process_positions[pid] = (x, y)
            
            # Draw process circle
            color = QColor('#ff5722') if pid in self.deadlocked_processes else QColor('#4caf50')
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor('white'), 2))
            painter.drawEllipse(x - 20, y - 20, 40, 40)
            
            # Draw label
            painter.setPen(QColor('white'))
            painter.drawText(x - 15, y + 5, f"P{pid}")
            
        # Draw resources (squares on right)
        resource_positions = {}
        resource_list = list(self.rag.resources.keys())
        m = len(resource_list)
        
        for i, rkey in enumerate(resource_list):
            angle = 2 * 3.14159 * i / max(m, 1) - 3.14159 / 2
            x = center_x + radius // 2 + int(radius * 0.3 * np.cos(angle))
            y = center_y + int(radius * 0.5 * np.sin(angle))
            resource_positions[rkey] = (x, y)
            
            # Draw resource square
            painter.setBrush(QBrush(QColor('#2196f3')))
            painter.setPen(QPen(QColor('white'), 2))
            painter.drawRect(x - 20, y - 20, 40, 40)
            
            # Draw label
            painter.setPen(QColor('white'))
            rtype, rid = rkey
            painter.drawText(x - 15, y + 5, f"{rtype.value[0]}{rid}")
            
        # Draw request edges (process -> resource, dotted)
        pen = QPen(QColor('#ff9800'), 2, Qt.DotLine)
        painter.setPen(pen)
        for pid, resources in self.rag.request_edges.items():
            if pid in process_positions:
                px, py = process_positions[pid]
                for rkey in resources:
                    if rkey in resource_positions:
                        rx, ry = resource_positions[rkey]
                        painter.drawLine(px + 20, py, rx - 20, ry)
                        # Arrow head
                        painter.drawLine(rx - 20, ry, rx - 30, ry - 5)
                        painter.drawLine(rx - 20, ry, rx - 30, ry + 5)
                        
        # Draw assignment edges (resource -> process, solid)
        pen = QPen(QColor('#4caf50'), 2, Qt.SolidLine)
        painter.setPen(pen)
        for rkey, pid in self.rag.assignment_edges.items():
            if pid is not None and rkey in resource_positions and pid in process_positions:
                rx, ry = resource_positions[rkey]
                px, py = process_positions[pid]
                painter.drawLine(rx - 20, ry, px + 20, py)
                # Arrow head
                painter.drawLine(px + 20, py, px + 30, py - 5)
                painter.drawLine(px + 20, py, px + 30, py + 5)
                
        painter.end()


class BankersTableWidget(QTableWidget):
    """Table widget for Banker's algorithm state display."""
    
    def __init__(self):
        super().__init__()
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Process", "Max", "Allocated", "Need"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
    def update_state(self, state: dict):
        """Update table with Banker's state."""
        processes = state.get('processes', {})
        
        self.setRowCount(len(processes))
        
        for i, (pid, pstate) in enumerate(processes.items()):
            # Simplify display - show total resources
            max_total = sum(pstate['max'].values())
            alloc_total = sum(pstate['allocated'].values())
            need_total = sum(pstate['needed'].values())
            
            self.setItem(i, 0, QTableWidgetItem(f"P{pid}"))
            self.setItem(i, 1, QTableWidgetItem(str(max_total)))
            self.setItem(i, 2, QTableWidgetItem(str(alloc_total)))
            self.setItem(i, 3, QTableWidgetItem(str(need_total)))
            
            # Color coding
            if need_total == 0:
                for col in range(4):
                    self.item(i, col).setBackground(QColor('#4caf50'))  # Green - finished
            elif alloc_total > 0:
                for col in range(4):
                    self.item(i, col).setBackground(QColor('#ff9800'))  # Orange - active


class DeadlockView(QWidget):
    """
    Deadlock detection and prevention visualization view.
    """
    
    def __init__(self):
        super().__init__()
        
        self.detector = DeadlockDetector()
        self.scheduler = None  # Will be set externally
        
        self.init_ui()
        
        # Simulation timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Vertical)
        
        # Top section - Resource Allocation Graph
        top_widget = QWidget()
        top_layout = QVBoxLayout()
        
        top_layout.addWidget(QLabel("<h3>Resource Allocation Graph</h3>"))
        
        # Graph visualization
        self.graph_widget = ResourceGraphWidget()
        top_layout.addWidget(self.graph_widget)
        
        # Legend
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(self._create_legend_item("Process", "#4caf50"))
        legend_layout.addWidget(self._create_legend_item("Resource", "#2196f3"))
        legend_layout.addWidget(self._create_legend_item("Request Edge", "#ff9800"))
        legend_layout.addWidget(self._create_legend_item("Assignment Edge", "#4caf50"))
        legend_layout.addWidget(self._create_legend_item("Deadlocked", "#ff5722"))
        legend_layout.addStretch()
        top_layout.addLayout(legend_layout)
        
        top_widget.setLayout(top_layout)
        splitter.addWidget(top_widget)
        
        # Middle section - Banker's Algorithm
        middle_widget = QWidget()
        middle_layout = QVBoxLayout()
        
        middle_layout.addWidget(QLabel("<h3>Banker's Algorithm - Safe State Detection</h3>"))
        
        # Available resources display
        avail_layout = QHBoxLayout()
        avail_layout.addWidget(QLabel("Available Resources:"))
        self.lbl_available = QLabel("-")
        avail_layout.addWidget(self.lbl_available)
        avail_layout.addStretch()
        middle_layout.addLayout(avail_layout)
        
        # Banker's table
        self.bankers_table = BankersTableWidget()
        middle_layout.addWidget(self.bankers_table)
        
        # Safety sequence
        safety_layout = QHBoxLayout()
        safety_layout.addWidget(QLabel("Safety Sequence:"))
        self.lbl_safety = QLabel("-")
        safety_layout.addWidget(self.lbl_safety)
        safety_layout.addStretch()
        middle_layout.addLayout(safety_layout)
        
        middle_widget.setLayout(middle_layout)
        splitter.addWidget(middle_widget)
        
        # Bottom section - Controls and Log
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout()
        
        # Controls
        controls_group = QGroupBox("Simulation Controls")
        controls_layout = QVBoxLayout()
        
        # Process count
        proc_layout = QHBoxLayout()
        proc_layout.addWidget(QLabel("Processes:"))
        self.spin_processes = QSpinBox()
        self.spin_processes.setRange(2, 10)
        self.spin_processes.setValue(5)
        proc_layout.addWidget(self.spin_processes)
        controls_layout.addLayout(proc_layout)
        
        # Resource count
        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("Resources:"))
        self.spin_resources = QSpinBox()
        self.spin_resources.setRange(2, 8)
        self.spin_resources.setValue(4)
        res_layout.addWidget(self.spin_resources)
        controls_layout.addLayout(res_layout)
        
        # Buttons
        btn_setup = QPushButton("Setup Scenario")
        btn_setup.clicked.connect(self.setup_scenario)
        controls_layout.addWidget(btn_setup)
        
        btn_detect = QPushButton("Detect Deadlock")
        btn_detect.clicked.connect(self.detect_deadlock)
        controls_layout.addWidget(btn_detect)
        
        btn_request = QPushButton("Simulate Request")
        btn_request.clicked.connect(self.simulate_request)
        controls_layout.addWidget(btn_request)
        
        btn_release = QPushButton("Release Resources")
        btn_release.clicked.connect(self.release_resources)
        controls_layout.addWidget(btn_release)
        
        controls_group.setLayout(controls_layout)
        bottom_layout.addWidget(controls_group)
        
        # Log output
        log_group = QGroupBox("Event Log")
        log_layout = QVBoxLayout()
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        log_layout.addWidget(self.txt_log)
        log_group.setLayout(log_layout)
        bottom_layout.addWidget(log_group)
        
        bottom_widget.setLayout(bottom_layout)
        splitter.addWidget(bottom_widget)
        
        # Set splitter sizes
        splitter.setSizes([300, 250, 200])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
        
        # Initial setup
        self.setup_scenario()
        
    def _create_legend_item(self, text: str, color: str) -> QWidget:
        """Create legend item with colored box."""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setSpacing(5)
        
        box = QLabel()
        box.setFixedSize(20, 20)
        box.setStyleSheet(f"background-color: {color}; border: 1px solid white;")
        layout.addWidget(box)
        
        label = QLabel(text)
        label.setStyleSheet("color: white;")
        layout.addWidget(label)
        
        widget.setLayout(layout)
        return widget
        
    def setup_scenario(self):
        """Setup a new deadlock detection scenario."""
        num_processes = self.spin_processes.value()
        num_resources = self.spin_resources.value()
        
        # Reset detector
        self.detector = DeadlockDetector()
        
        # Setup Banker's algorithm
        available = {rt: 10 for rt in ResourceType}
        total = {rt: 15 for rt in ResourceType}
        self.detector.setup_bankers(available, total)
        
        # Add processes
        for pid in range(1, num_processes + 1):
            max_demand = {
                ResourceType.CPU: np.random.randint(1, 5),
                ResourceType.MEMORY: np.random.randint(2, 8),
                ResourceType.DISK: np.random.randint(1, 4)
            }
            self.detector.bankers.add_process(pid, max_demand)
            
        # Add to RAG
        for pid in range(1, num_processes + 1):
            self.detector.rag.add_process(pid)
            
        for rid in range(num_resources):
            for rt in [ResourceType.CPU, ResourceType.MEMORY]:
                self.detector.rag.add_resource(rt, rid)
                
        # Initial allocations
        for pid in range(1, num_processes + 1):
            for rt in [ResourceType.CPU, ResourceType.MEMORY]:
                if np.random.random() > 0.3:
                    amount = np.random.randint(1, 3)
                    self.detector.bankers.allocate(pid, rt, amount)
                    self.detector.rag.allocate_resource(pid, rt, 0)
                    
        self.log("Scenario setup complete")
        self.update_display()
        
    def detect_deadlock(self):
        """Run deadlock detection."""
        has_deadlock, processes, explanation = self.detector.detect_deadlock()
        
        if has_deadlock:
            self.log(f"⚠️ DEADLOCK DETECTED!")
            self.log(f"Deadlocked processes: {processes}")
            self.log(f"Explanation: {explanation}")
            
            # Show recovery suggestions
            suggestions = self.detector.suggest_recovery(processes)
            self.log("\nRecovery Suggestions:")
            for s in suggestions:
                self.log(s)
        else:
            self.log("✅ No deadlock detected")
            self.log(f"Safe state confirmed. Safety sequence exists.")
            
        # Check sync deadlocks too
        has_sync, sync_procs = self.detector.detect_sync_deadlock()
        if has_sync:
            self.log(f"⚠️ Synchronization deadlock detected: {sync_procs}")
            
        self.update_display()
        
    def simulate_request(self):
        """Simulate a resource request."""
        if not self.detector.bankers:
            return
            
        # Pick random process and resource type
        pid = np.random.randint(1, self.spin_processes.value() + 1)
        rt = np.random.choice([ResourceType.CPU, ResourceType.MEMORY, ResourceType.DISK])
        amount = np.random.randint(1, 3)
        
        is_safe, reason = self.detector.check_request_safety(pid, rt, amount)
        
        self.log(f"Request: P{pid} requests {amount} {rt.value}")
        self.log(f"Result: {'✅ GRANTED' if is_safe else '❌ DENIED'} - {reason}")
        
        if is_safe:
            self.detector.rag.request_resource(pid, rt, 0)
            self.detector.rag.allocate_resource(pid, rt, 0)
            
        self.update_display()
        
    def release_resources(self):
        """Release resources from a random process."""
        if not self.detector.bankers:
            return
            
        pid = np.random.randint(1, self.spin_processes.value() + 1)
        rt = np.random.choice([ResourceType.CPU, ResourceType.MEMORY])
        
        state = self.detector.bankers.processes.get(pid)
        if state:
            amount = state.allocated.get(rt, 0)
            if amount > 0:
                self.detector.bankers.release(pid, rt, amount)
                self.detector.rag.release_resource(rt, 0)
                self.log(f"Released: P{pid} released {amount} {rt.value}")
                self.update_display()
                
    def update_display(self):
        """Update all visual components."""
        if self.detector.rag:
            # Detect deadlock for highlighting
            has_deadlock, deadlocked, _ = self.detector.detect_deadlock()
            self.graph_widget.set_graph(self.detector.rag, deadlocked)
            
        if self.detector.bankers:
            state = self.detector.bankers.get_state()
            self.bankers_table.update_state(state)
            
            # Update available
            avail_str = ", ".join(f"{k}={v}" for k, v in state['available'].items())
            self.lbl_available.setText(avail_str)
            
            # Update safety sequence
            if state['is_safe']:
                safety = " → ".join(f"P{p}" for p in state['safety_sequence'])
                self.lbl_safety.setText(f"✅ {safety}")
            else:
                self.lbl_safety.setText("❌ Unsafe state!")
                
    def update_simulation(self):
        """Periodic simulation update."""
        self.update_display()
        
    def log(self, message: str):
        """Add message to log."""
        self.txt_log.append(message)
