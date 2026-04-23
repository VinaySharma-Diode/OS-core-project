from PyQt5.QtWidgets import QMainWindow, QStackedWidget, QListWidget, QWidget, QHBoxLayout, QLabel, QVBoxLayout
from ui.simulation_view import SimulationView
from ui.analysis_view import AnalysisView
from ui.settings_view import SettingsView
from ui.memory_view import MemoryView
from ui.process_view import ProcessView
from ui.scheduling_view import SchedulingView
from ui.deadlock_view import DeadlockView
from ui.shell_view import ShellView
from ui.raid_view import RAIDView


class HomeView(QWidget):
    """Home view with welcome message."""
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        
        title = QLabel("OS Core Simulator")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #4CAF50;")
        
        subtitle = QLabel("Comprehensive Operating System Simulation Platform")
        subtitle.setStyleSheet("font-size: 14px; color: #888;")
        
        features = QLabel(
            "Features:\n"
            "• Disk Management - File allocation, fragmentation, defragmentation\n"
            "• Memory Management - Paging, virtual memory, page replacement\n"
            "• Process Scheduling - CPU and I/O scheduling algorithms\n"
            "• Disk Scheduling - FCFS, SSTF, SCAN, C-SCAN, LOOK, C-LOOK\n"
            "• Cache Management - LRU, LFU, FIFO replacement policies\n"
            "• Deadlock Detection - Banker's algorithm, Resource allocation graph\n"
            "• Synchronization - Semaphores, Mutexes, RW Locks, Barriers\n"
            "• IPC - Shared memory, Message queues, Pipes, Signals\n"
            "• RAID Simulation - RAID 0, 1, 5, 6 with failure recovery\n"
            "• Interactive Shell - Command-line interface to all subsystems\n"
            "• Performance Analysis - Metrics and visualization"
        )
        features.setStyleSheet("font-size: 12px; color: #ccc; margin-top: 20px;")
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(features)
        layout.addStretch()
        
        self.setLayout(layout)


class Dashboard(QMainWindow):
    """
    Main application window with sidebar navigation.
    Enhanced for OS Core functionality.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("OS Core Simulator")
        self.setGeometry(100, 100, 1400, 800)

        # Sidebar navigation
        self.sidebar = QListWidget()
        self.sidebar.addItems([
            "Home",
            "Interactive Shell",
            "Disk Simulation",
            "RAID Array",
            "Memory Management",
            "Process Scheduling",
            "Disk Scheduling",
            "Deadlock Detection",
            "Performance Analysis",
            "Settings"
        ])
        self.sidebar.currentRowChanged.connect(self.display)

        # Stacked views
        self.stack = QStackedWidget()
        self.stack.addWidget(HomeView())
        self.stack.addWidget(ShellView())           # Interactive Shell
        self.stack.addWidget(SimulationView())      # Disk Simulation
        self.stack.addWidget(RAIDView())            # RAID Array
        self.stack.addWidget(MemoryView())          # Memory Management
        self.stack.addWidget(ProcessView())         # Process Scheduling
        self.stack.addWidget(SchedulingView())     # Disk Scheduling
        self.stack.addWidget(DeadlockView())       # Deadlock Detection
        self.stack.addWidget(AnalysisView())        # Performance Analysis
        self.stack.addWidget(SettingsView())       # Settings

        # Layout
        layout = QHBoxLayout()
        layout.addWidget(self.sidebar, 2)
        layout.addWidget(self.stack, 8)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def display(self, index):
        """
        Switch view based on sidebar selection.
        """
        self.stack.setCurrentIndex(index)
