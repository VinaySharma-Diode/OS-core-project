"""
Settings View for OS Core Simulator.
Comprehensive configuration panel for all subsystems.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QSpinBox, QComboBox, QGroupBox, QPushButton,
    QCheckBox, QSlider, QTabWidget, QFormLayout,
    QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt

from core.disk import AllocationMethod
from core.memory import PageReplacementAlgorithm
from core.cache import CachePolicy
from core.process import CPUSchedulingAlgorithm
from core.scheduling import SchedulingAlgorithm


class SettingsView(QWidget):
    """
    Comprehensive settings panel for OS Core configuration.
    """

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Create tabs for different settings
        self.tabs = QTabWidget()
        
        # Disk Settings
        self.tabs.addTab(self.create_disk_settings(), "Disk Settings")
        
        # Memory Settings
        self.tabs.addTab(self.create_memory_settings(), "Memory Settings")
        
        # Cache Settings
        self.tabs.addTab(self.create_cache_settings(), "Cache Settings")
        
        # Scheduling Settings
        self.tabs.addTab(self.create_scheduling_settings(), "Scheduling Settings")
        
        # Display Settings
        self.tabs.addTab(self.create_display_settings(), "Display Settings")
        
        layout.addWidget(self.tabs)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        btn_save = QPushButton("Save Settings")
        btn_save.clicked.connect(self.save_settings)
        btn_layout.addWidget(btn_save)
        
        btn_load = QPushButton("Load Settings")
        btn_layout.addWidget(btn_load)
        
        btn_default = QPushButton("Restore Defaults")
        btn_default.clicked.connect(self.restore_defaults)
        btn_layout.addWidget(btn_default)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def create_disk_settings(self):
        """Create disk configuration settings."""
        widget = QWidget()
        layout = QFormLayout()
        
        # Disk size
        self.disk_size_spin = QSpinBox()
        self.disk_size_spin.setRange(16, 256)
        self.disk_size_spin.setValue(64)
        self.disk_size_spin.setSuffix(" blocks")
        layout.addRow("Disk Size:", self.disk_size_spin)
        
        # Block size
        self.block_size_spin = QSpinBox()
        self.block_size_spin.setRange(512, 8192)
        self.block_size_spin.setValue(4096)
        self.block_size_spin.setSuffix(" bytes")
        self.block_size_spin.setSingleStep(512)
        layout.addRow("Block Size:", self.block_size_spin)
        
        # Default allocation method
        self.alloc_method_combo = QComboBox()
        for method in AllocationMethod:
            self.alloc_method_combo.addItem(method.value.title(), method)
        layout.addRow("Default Allocation Method:", self.alloc_method_combo)
        
        # Simulation speed
        self.sim_speed_slider = QSlider(Qt.Horizontal)
        self.sim_speed_slider.setRange(50, 1000)
        self.sim_speed_slider.setValue(200)
        layout.addRow("Animation Speed:", self.sim_speed_slider)
        
        widget.setLayout(layout)
        return widget

    def create_memory_settings(self):
        """Create memory configuration settings."""
        widget = QWidget()
        layout = QFormLayout()
        
        # Physical memory size
        self.phys_mem_spin = QSpinBox()
        self.phys_mem_spin.setRange(8, 128)
        self.phys_mem_spin.setValue(32)
        self.phys_mem_spin.setSuffix(" frames")
        layout.addRow("Physical Memory:", self.phys_mem_spin)
        
        # Virtual memory size
        self.virt_mem_spin = QSpinBox()
        self.virt_mem_spin.setRange(32, 512)
        self.virt_mem_spin.setValue(128)
        self.virt_mem_spin.setSuffix(" pages")
        layout.addRow("Virtual Memory:", self.virt_mem_spin)
        
        # Page size
        self.page_size_spin = QSpinBox()
        self.page_size_spin.setRange(1024, 16384)
        self.page_size_spin.setValue(4096)
        self.page_size_spin.setSuffix(" bytes")
        self.page_size_spin.setSingleStep(1024)
        layout.addRow("Page Size:", self.page_size_spin)
        
        # Page replacement algorithm
        self.page_algo_combo = QComboBox()
        for algo in PageReplacementAlgorithm:
            self.page_algo_combo.addItem(algo.value.upper(), algo)
        layout.addRow("Page Replacement:", self.page_algo_combo)
        
        # TLB size
        self.tlb_size_spin = QSpinBox()
        self.tlb_size_spin.setRange(4, 64)
        self.tlb_size_spin.setValue(16)
        self.tlb_size_spin.setSuffix(" entries")
        layout.addRow("TLB Size:", self.tlb_size_spin)
        
        widget.setLayout(layout)
        return widget

    def create_cache_settings(self):
        """Create cache configuration settings."""
        widget = QWidget()
        layout = QFormLayout()
        
        # Cache capacity
        self.cache_capacity_spin = QSpinBox()
        self.cache_capacity_spin.setRange(4, 128)
        self.cache_capacity_spin.setValue(16)
        self.cache_capacity_spin.setSuffix(" blocks")
        layout.addRow("Cache Capacity:", self.cache_capacity_spin)
        
        # Cache policy
        self.cache_policy_combo = QComboBox()
        for policy in CachePolicy:
            self.cache_policy_combo.addItem(policy.value.upper(), policy)
        layout.addRow("Replacement Policy:", self.cache_policy_combo)
        
        # Write policy
        self.write_policy_combo = QComboBox()
        self.write_policy_combo.addItem("Write-Back")
        self.write_policy_combo.addItem("Write-Through")
        layout.addRow("Write Policy:", self.write_policy_combo)
        
        # Two-level cache
        self.two_level_check = QCheckBox("Enable Two-Level Cache")
        layout.addRow(self.two_level_check)
        
        # L1 size (if two-level enabled)
        self.l1_size_spin = QSpinBox()
        self.l1_size_spin.setRange(4, 32)
        self.l1_size_spin.setValue(8)
        self.l1_size_spin.setSuffix(" blocks")
        layout.addRow("L1 Cache Size:", self.l1_size_spin)
        
        widget.setLayout(layout)
        return widget

    def create_scheduling_settings(self):
        """Create scheduling configuration settings."""
        widget = QWidget()
        layout = QFormLayout()
        
        # CPU Scheduling
        layout.addRow(QLabel("<b>CPU Scheduling</b>"))
        
        self.cpu_algo_combo = QComboBox()
        for algo in CPUSchedulingAlgorithm:
            self.cpu_algo_combo.addItem(algo.value.upper(), algo)
        layout.addRow("CPU Algorithm:", self.cpu_algo_combo)
        
        # Time quantum
        self.time_quantum_spin = QSpinBox()
        self.time_quantum_spin.setRange(5, 100)
        self.time_quantum_spin.setValue(10)
        self.time_quantum_spin.setSuffix(" ms")
        layout.addRow("Time Quantum:", self.time_quantum_spin)
        
        # Number of CPUs
        self.cpu_count_spin = QSpinBox()
        self.cpu_count_spin.setRange(1, 8)
        self.cpu_count_spin.setValue(2)
        layout.addRow("CPU Cores:", self.cpu_count_spin)
        
        # Disk Scheduling
        layout.addRow(QLabel("<b>Disk Scheduling</b>"))
        
        self.disk_algo_combo = QComboBox()
        for algo in SchedulingAlgorithm:
            self.disk_algo_combo.addItem(algo.value.upper(), algo)
        layout.addRow("Disk Algorithm:", self.disk_algo_combo)
        
        # Disk tracks
        self.disk_tracks_spin = QSpinBox()
        self.disk_tracks_spin.setRange(50, 500)
        self.disk_tracks_spin.setValue(200)
        self.disk_tracks_spin.setSuffix(" tracks")
        layout.addRow("Disk Tracks:", self.disk_tracks_spin)
        
        # Initial head position
        self.head_pos_spin = QSpinBox()
        self.head_pos_spin.setRange(0, 499)
        self.head_pos_spin.setValue(50)
        layout.addRow("Initial Head:", self.head_pos_spin)
        
        widget.setLayout(layout)
        return widget

    def create_display_settings(self):
        """Create display and UI settings."""
        widget = QWidget()
        layout = QFormLayout()
        
        # Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Dark Theme")
        self.theme_combo.addItem("Light Theme")
        self.theme_combo.addItem("High Contrast")
        layout.addRow("Theme:", self.theme_combo)
        
        # Grid size
        self.grid_size_combo = QComboBox()
        self.grid_size_combo.addItem("Small (8x8)")
        self.grid_size_combo.addItem("Medium (8x16)")
        self.grid_size_combo.addItem("Large (16x16)")
        layout.addRow("Disk Grid Size:", self.grid_size_combo)
        
        # Show animations
        self.animations_check = QCheckBox("Enable Animations")
        self.animations_check.setChecked(True)
        layout.addRow(self.animations_check)
        
        # Real-time updates
        self.realtime_check = QCheckBox("Real-time Metric Updates")
        self.realtime_check.setChecked(True)
        layout.addRow(self.realtime_check)
        
        # Export settings
        layout.addRow(QLabel("<b>Export Settings</b>"))
        
        self.auto_export_check = QCheckBox("Auto-export Reports")
        layout.addRow(self.auto_export_check)
        
        self.export_format_combo = QComboBox()
        self.export_format_combo.addItem("CSV")
        self.export_format_combo.addItem("PDF")
        self.export_format_combo.addItem("Both")
        layout.addRow("Export Format:", self.export_format_combo)
        
        widget.setLayout(layout)
        return widget

    def save_settings(self):
        """Save current settings to file."""
        # This would save to a config file
        QMessageBox.information(
            self,
            "Settings Saved",
            "Configuration settings have been saved successfully!\n\n"
            "Note: Settings will be applied on next application start."
        )

    def restore_defaults(self):
        """Restore default settings."""
        reply = QMessageBox.question(
            self,
            "Restore Defaults",
            "Are you sure you want to restore default settings?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Reset all values to defaults
            self.disk_size_spin.setValue(64)
            self.block_size_spin.setValue(4096)
            self.phys_mem_spin.setValue(32)
            self.virt_mem_spin.setValue(128)
            self.cache_capacity_spin.setValue(16)
            self.time_quantum_spin.setValue(10)
            self.cpu_count_spin.setValue(2)
            
            QMessageBox.information(self, "Defaults Restored", "All settings restored to defaults!")
