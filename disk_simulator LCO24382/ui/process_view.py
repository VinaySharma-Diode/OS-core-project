"""
Process Scheduling View for OS Core Simulator.
Visualizes process states, CPU scheduling, and I/O operations.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QGridLayout, QComboBox, QSpinBox, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QTabWidget, QTextEdit
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from core.process import ProcessScheduler, CPUSchedulingAlgorithm, ProcessState, ProcessType

import random
import time


class ProcessView(QWidget):
    """
    Process scheduling visualization with state transitions.
    """
    
    def __init__(self):
        super().__init__()
        self.scheduler = ProcessScheduler(num_cpus=2, time_quantum=10)
        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        self.current_time = 0
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Control panel
        controls = QHBoxLayout()
        
        # Algorithm selector
        controls.addWidget(QLabel("Algorithm:"))
        self.algo_combo = QComboBox()
        for algo in CPUSchedulingAlgorithm:
            self.algo_combo.addItem(algo.value.upper(), algo)
        self.algo_combo.currentIndexChanged.connect(self.change_algorithm)
        controls.addWidget(self.algo_combo)
        
        # Process creator
        controls.addWidget(QLabel("Count:"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 5)
        self.count_spin.setValue(3)
        controls.addWidget(self.count_spin)
        
        btn_create = QPushButton("Create Processes")
        btn_create.clicked.connect(self.create_processes)
        controls.addWidget(btn_create)
        
        btn_start = QPushButton("Start Simulation")
        btn_start.clicked.connect(self.start_simulation)
        controls.addWidget(btn_start)
        
        btn_stop = QPushButton("Stop")
        btn_stop.clicked.connect(self.stop_simulation)
        controls.addWidget(btn_stop)
        
        btn_reset = QPushButton("Reset")
        btn_reset.clicked.connect(self.reset_scheduler)
        controls.addWidget(btn_reset)
        
        layout.addLayout(controls)
        
        # CPU visualization
        cpu_group = QGroupBox("CPU Status")
        cpu_layout = QHBoxLayout()
        
        self.cpu_widgets = []
        for i in range(2):
            cpu_widget = QWidget()
            cpu_vlayout = QVBoxLayout()
            
            label = QLabel(f"CPU {i}")
            label.setStyleSheet("font-weight: bold;")
            cpu_vlayout.addWidget(label)
            
            status = QLabel("Idle")
            status.setStyleSheet("color: #888;")
            cpu_vlayout.addWidget(status)
            
            progress = QProgressBar()
            progress.setMaximum(100)
            progress.setValue(0)
            cpu_vlayout.addWidget(progress)
            
            cpu_widget.setLayout(cpu_vlayout)
            cpu_layout.addWidget(cpu_widget)
            
            self.cpu_widgets.append({
                "status": status,
                "progress": progress
            })
        
        cpu_group.setLayout(cpu_layout)
        layout.addWidget(cpu_group)
        
        # Process table
        self.process_table = QTableWidget()
        self.process_table.setColumnCount(6)
        self.process_table.setHorizontalHeaderLabels([
            "PID", "Name", "State", "Priority", "CPU Time", "Remaining"
        ])
        self.process_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.process_table)
        
        # Statistics
        stats_layout = QHBoxLayout()
        
        self.stats_label = QLabel(
            "Processes: 0 | Completed: 0 | Context Switches: 0\n"
            "Avg Turnaround: 0ms | CPU Utilization: 0%"
        )
        self.stats_label.setStyleSheet("font-family: monospace; padding: 10px;")
        stats_layout.addWidget(self.stats_label)
        
        layout.addLayout(stats_layout)
        
        # Queue visualization
        queue_group = QGroupBox("Ready Queue")
        queue_layout = QHBoxLayout()
        self.queue_label = QLabel("Empty")
        self.queue_label.setStyleSheet("color: #888; font-style: italic;")
        queue_layout.addWidget(self.queue_label)
        queue_group.setLayout(queue_layout)
        layout.addWidget(queue_group)
        
        self.setLayout(layout)
    
    def change_algorithm(self, index):
        """Change CPU scheduling algorithm."""
        algo = self.algo_combo.currentData()
        self.scheduler.set_algorithm(algo)
    
    def create_processes(self):
        """Create random processes."""
        count = self.count_spin.value()
        process_types = [ProcessType.CPU_BOUND, ProcessType.IO_BOUND, ProcessType.INTERACTIVE]
        
        for i in range(count):
            ptype = random.choice(process_types)
            burst = random.randint(50, 200)
            priority = random.randint(1, 10)
            io_ops = 3 if ptype == ProcessType.IO_BOUND else 0
            
            self.scheduler.create_process(
                name=f"Process_{len(self.scheduler.all_processes) + 1}",
                burst_time=burst,
                priority=priority,
                process_type=ptype,
                io_ops=io_ops
            )
        
        self.update_display()
    
    def start_simulation(self):
        """Start the simulation timer."""
        self.timer.start(500)  # 500ms tick
    
    def stop_simulation(self):
        """Stop the simulation timer."""
        self.timer.stop()
    
    def reset_scheduler(self):
        """Reset the scheduler."""
        self.scheduler.reset()
        self.current_time = 0
        self.update_display()
    
    def tick(self):
        """Simulation tick."""
        self.scheduler.schedule(self.current_time)
        self.current_time += 1
        
        # Update I/O
        completed_io = []
        for cpu in self.scheduler.cpus:
            if cpu.current_process:
                # Simulate execution
                cpu.current_process.cpu_time_used += 1
                cpu.current_process.remaining_time -= 1
                cpu.busy_time += 1
        
        self.update_display()
    
    def update_display(self):
        """Update the process visualization."""
        # Update CPU widgets
        for i, cpu in enumerate(self.scheduler.cpus):
            widget = self.cpu_widgets[i]
            
            if cpu.current_process:
                pid = cpu.current_process.pid
                widget["status"].setText(f"Running P{pid}")
                widget["status"].setStyleSheet("color: #4CAF50; font-weight: bold;")
                
                # Progress based on completion
                total = cpu.current_process.burst_time
                done = total - cpu.current_process.remaining_time
                progress = int((done / total) * 100)
                widget["progress"].setValue(progress)
            else:
                widget["status"].setText("Idle")
                widget["status"].setStyleSheet("color: #888;")
                widget["progress"].setValue(0)
        
        # Update process table
        processes = self.scheduler.get_process_list()
        self.process_table.setRowCount(len(processes))
        
        state_colors = {
            ProcessState.NEW: "#2196F3",
            ProcessState.READY: "#FF9800",
            ProcessState.RUNNING: "#4CAF50",
            ProcessState.WAITING: "#9C27B0",
            ProcessState.TERMINATED: "#F44336"
        }
        
        for row, proc in enumerate(processes):
            self.process_table.setItem(row, 0, QTableWidgetItem(str(proc.pid)))
            self.process_table.setItem(row, 1, QTableWidgetItem(proc.name))
            
            state_item = QTableWidgetItem(proc.state.name)
            state_item.setForeground(QColor(state_colors.get(proc.state, "#888")))
            self.process_table.setItem(row, 2, state_item)
            
            self.process_table.setItem(row, 3, QTableWidgetItem(str(proc.priority)))
            self.process_table.setItem(row, 4, QTableWidgetItem(f"{proc.cpu_time_used:.0f}"))
            self.process_table.setItem(row, 5, QTableWidgetItem(f"{proc.remaining_time:.0f}"))
        
        # Update statistics
        stats = self.scheduler.get_statistics()
        self.stats_label.setText(
            f"Processes: {stats['total_processes']} | "
            f"Completed: {stats['completed']} | "
            f"Context Switches: {sum(c.context_switches for c in self.scheduler.cpus)}\n"
            f"Avg Turnaround: {stats['avg_turnaround']:.1f}ms | "
            f"CPU Utilization: {stats['cpu_utilization']:.1%}"
        )
        
        # Update queue visualization
        queue_pids = [str(p.pid) for p in self.scheduler.ready_queue]
        self.queue_label.setText(
            " → ".join(queue_pids) if queue_pids else "Empty"
        )
