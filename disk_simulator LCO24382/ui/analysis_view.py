"""
Analysis View for OS Core Simulator.
Comprehensive performance analysis and visualization.
"""

import random
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTabWidget, QGroupBox, QGridLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton
)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import numpy as np

from core.disk import Disk, AllocationMethod
from core.performance import calculate_metrics, generate_performance_report
from core.fragmentation import get_fragmentation_report
from core.cache import DiskCache, CachePolicy
from core.memory import MemoryManager, PageReplacementAlgorithm
from core.process import ProcessScheduler, CPUSchedulingAlgorithm
from core.scheduling import DiskScheduler, SchedulingAlgorithm, compare_algorithms
from core.network import NetworkStack
from core.security import SecurityManager
from core.raid import RAIDArray, RAIDLevel


class AnalysisView(QWidget):
    """
    Comprehensive analysis view showing OS Core performance metrics.
    """

    def __init__(self):
        super().__init__()
        
        # Initialize subsystems
        self.disk = Disk(size=64)
        self.cache = DiskCache(capacity=16)
        self.memory = MemoryManager(physical_memory_size=32)
        self.scheduler = ProcessScheduler(num_cpus=2)
        self.disk_scheduler = DiskScheduler(total_tracks=200)
        self.network = NetworkStack()
        self.security = SecurityManager()
        self.raid = RAIDArray(RAIDLevel.RAID_5, disk_size=100, num_disks=4)
        
        self.init_ui()
        self.generate_sample_data()
        self.update_all_charts()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Create tabs for different analyses
        self.tabs = QTabWidget()

        # Disk Analysis Tab
        self.tabs.addTab(self.create_disk_tab(), "Disk Performance")

        # Scheduling Comparison Tab
        self.tabs.addTab(self.create_scheduling_tab(), "Scheduling Comparison")

        # Memory Analysis Tab
        self.tabs.addTab(self.create_memory_tab(), "Memory Analysis")

        # Cache Analysis Tab
        self.tabs.addTab(self.create_cache_tab(), "Cache Performance")

        # RAID Analysis Tab
        self.tabs.addTab(self.create_raid_tab(), "RAID Performance")

        # Network Analysis Tab
        self.tabs.addTab(self.create_network_tab(), "Network I/O")

        # Security Analysis Tab
        self.tabs.addTab(self.create_security_tab(), "Security Audit")

        # System Overview Tab
        self.tabs.addTab(self.create_overview_tab(), "System Overview")
        
        layout.addWidget(self.tabs)
        
        # Refresh button
        btn_refresh = QPushButton("Refresh All Metrics")
        btn_refresh.clicked.connect(self.update_all_charts)
        layout.addWidget(btn_refresh)
        
        self.setLayout(layout)

    def create_disk_tab(self):
        """Create disk performance analysis tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Charts
        charts_layout = QHBoxLayout()
        
        # Fragmentation chart
        frag_group = QGroupBox("Fragmentation Analysis")
        frag_layout = QVBoxLayout()
        self.fig_frag, self.ax_frag = plt.subplots(figsize=(5, 3))
        self.canvas_frag = FigureCanvas(self.fig_frag)
        frag_layout.addWidget(self.canvas_frag)
        frag_group.setLayout(frag_layout)
        charts_layout.addWidget(frag_group)
        
        # Allocation method chart
        alloc_group = QGroupBox("Allocation Methods")
        alloc_layout = QVBoxLayout()
        self.fig_alloc, self.ax_alloc = plt.subplots(figsize=(5, 3))
        self.canvas_alloc = FigureCanvas(self.fig_alloc)
        alloc_layout.addWidget(self.canvas_alloc)
        alloc_group.setLayout(alloc_layout)
        charts_layout.addWidget(alloc_group)
        
        layout.addLayout(charts_layout)
        
        # Metrics table
        self.disk_metrics_table = QTableWidget()
        self.disk_metrics_table.setColumnCount(2)
        self.disk_metrics_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.disk_metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.disk_metrics_table)
        
        widget.setLayout(layout)
        return widget

    def create_scheduling_tab(self):
        """Create scheduling algorithm comparison tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Comparison chart
        sched_group = QGroupBox("Disk Scheduling Algorithm Comparison")
        sched_layout = QVBoxLayout()
        self.fig_sched, self.ax_sched = plt.subplots(figsize=(8, 4))
        self.canvas_sched = FigureCanvas(self.fig_sched)
        sched_layout.addWidget(self.canvas_sched)
        sched_group.setLayout(sched_layout)
        layout.addWidget(sched_group)
        
        # Comparison table
        self.sched_table = QTableWidget()
        self.sched_table.setColumnCount(5)
        self.sched_table.setHorizontalHeaderLabels([
            "Algorithm", "Total Seek", "Avg Seek", "Throughput", "Winner"
        ])
        self.sched_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.sched_table)
        
        widget.setLayout(layout)
        return widget

    def create_memory_tab(self):
        """Create memory management analysis tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Page replacement comparison
        mem_group = QGroupBox("Page Replacement Algorithm Comparison")
        mem_layout = QVBoxLayout()
        self.fig_mem, self.ax_mem = plt.subplots(figsize=(8, 4))
        self.canvas_mem = FigureCanvas(self.fig_mem)
        mem_layout.addWidget(self.canvas_mem)
        mem_group.setLayout(mem_layout)
        layout.addWidget(mem_group)
        
        # Memory stats
        self.mem_stats_label = QLabel("Memory statistics will appear here")
        self.mem_stats_label.setStyleSheet("font-family: monospace; padding: 10px;")
        layout.addWidget(self.mem_stats_label)
        
        widget.setLayout(layout)
        return widget

    def create_cache_tab(self):
        """Create cache performance analysis tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Cache policy comparison
        cache_group = QGroupBox("Cache Policy Comparison")
        cache_layout = QVBoxLayout()
        self.fig_cache, self.ax_cache = plt.subplots(figsize=(8, 4))
        self.canvas_cache = FigureCanvas(self.fig_cache)
        cache_layout.addWidget(self.canvas_cache)
        cache_group.setLayout(cache_layout)
        layout.addWidget(cache_group)
        
        # Cache metrics
        self.cache_metrics_table = QTableWidget()
        self.cache_metrics_table.setColumnCount(3)
        self.cache_metrics_table.setHorizontalHeaderLabels(["Policy", "Hit Rate", "Evictions"])
        self.cache_metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.cache_metrics_table)
        
        widget.setLayout(layout)
        return widget

    def create_overview_tab(self):
        """Create system overview tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Summary grid
        summary_layout = QGridLayout()
        
        # Disk summary
        disk_group = QGroupBox("Disk Summary")
        disk_layout = QVBoxLayout()
        self.disk_summary = QLabel("Disk metrics...")
        self.disk_summary.setStyleSheet("font-family: monospace;")
        disk_layout.addWidget(self.disk_summary)
        disk_group.setLayout(disk_layout)
        summary_layout.addWidget(disk_group, 0, 0)
        
        # Memory summary
        mem_group = QGroupBox("Memory Summary")
        mem_layout = QVBoxLayout()
        self.mem_summary = QLabel("Memory metrics...")
        self.mem_summary.setStyleSheet("font-family: monospace;")
        mem_layout.addWidget(self.mem_summary)
        mem_group.setLayout(mem_layout)
        summary_layout.addWidget(mem_group, 0, 1)
        
        # Cache summary
        cache_group = QGroupBox("Cache Summary")
        cache_layout = QVBoxLayout()
        self.cache_summary = QLabel("Cache metrics...")
        self.cache_summary.setStyleSheet("font-family: monospace;")
        cache_layout.addWidget(self.cache_summary)
        cache_group.setLayout(cache_layout)
        summary_layout.addWidget(cache_group, 1, 0)
        
        # Process summary
        proc_group = QGroupBox("Process Summary")
        proc_layout = QVBoxLayout()
        self.proc_summary = QLabel("Process metrics...")
        self.proc_summary.setStyleSheet("font-family: monospace;")
        proc_layout.addWidget(self.proc_summary)
        proc_group.setLayout(proc_layout)
        summary_layout.addWidget(proc_group, 1, 1)
        
        layout.addLayout(summary_layout)
        
        # Overall performance chart
        perf_group = QGroupBox("Overall System Performance")
        perf_layout = QVBoxLayout()
        self.fig_perf, self.ax_perf = plt.subplots(figsize=(8, 4))
        self.canvas_perf = FigureCanvas(self.fig_perf)
        perf_layout.addWidget(self.canvas_perf)
        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)
        
        widget.setLayout(layout)
        return widget

    def create_raid_tab(self):
        """Create RAID performance analysis tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        # RAID comparison chart
        raid_group = QGroupBox("RAID Level Comparison")
        raid_layout = QVBoxLayout()
        self.fig_raid, self.ax_raid = plt.subplots(figsize=(8, 4))
        self.canvas_raid = FigureCanvas(self.fig_raid)
        raid_layout.addWidget(self.canvas_raid)
        raid_group.setLayout(raid_layout)
        layout.addWidget(raid_group)

        # RAID metrics table
        self.raid_table = QTableWidget()
        self.raid_table.setColumnCount(4)
        self.raid_table.setHorizontalHeaderLabels(["Level", "Usable %", "Redundancy", "Performance"])
        self.raid_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.raid_table)

        widget.setLayout(layout)
        return widget

    def create_network_tab(self):
        """Create network I/O analysis tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        # Network traffic chart
        net_group = QGroupBox("Network Traffic Statistics")
        net_layout = QVBoxLayout()
        self.fig_net, self.ax_net = plt.subplots(figsize=(8, 4))
        self.canvas_net = FigureCanvas(self.fig_net)
        net_layout.addWidget(self.canvas_net)
        net_group.setLayout(net_layout)
        layout.addWidget(net_group)

        # Network metrics
        self.net_metrics_label = QLabel("Network statistics will appear here")
        self.net_metrics_label.setStyleSheet("font-family: monospace; padding: 10px;")
        layout.addWidget(self.net_metrics_label)

        widget.setLayout(layout)
        return widget

    def create_security_tab(self):
        """Create security audit analysis tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        # Security overview
        sec_group = QGroupBox("Security Metrics")
        sec_layout = QVBoxLayout()

        self.sec_label = QLabel("Security statistics will appear here")
        self.sec_label.setStyleSheet("font-family: monospace; padding: 10px;")
        sec_layout.addWidget(self.sec_label)

        # Audit log table
        self.audit_table = QTableWidget()
        self.audit_table.setColumnCount(4)
        self.audit_table.setHorizontalHeaderLabels(["Time", "User", "Action", "Status"])
        self.audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        sec_layout.addWidget(self.audit_table)

        sec_group.setLayout(sec_layout)
        layout.addWidget(sec_group)

        widget.setLayout(layout)
        return widget

    def generate_sample_data(self):
        """Generate sample data for analysis."""
        # Generate disk files
        import random
        for i in range(5):
            try:
                method = random.choice(list(AllocationMethod))
                self.disk.create_file(f"File{i+1}", random.randint(3, 8), method)
            except:
                pass
        
        # Generate disk scheduling requests
        for _ in range(10):
            self.disk_scheduler.add_request(random.randint(0, 199))
        
        # Generate memory accesses
        self.memory.create_page_table(1)
        for _ in range(50):
            page = random.randint(0, 127)
            self.memory.access_page(1, page)
        
        # Generate cache accesses
        for _ in range(100):
            block = random.randint(0, 63)
            if random.random() < 0.7:  # 70% read
                self.cache.get(block)
            else:
                self.cache.put(block, f"data_{block}".encode())

    def update_all_charts(self):
        """Update all charts and metrics."""
        self.update_disk_charts()
        self.update_scheduling_charts()
        self.update_memory_charts()
        self.update_cache_charts()
        self.update_raid_charts()
        self.update_network_charts()
        self.update_security_charts()
        self.update_overview()

    def update_disk_charts(self):
        """Update disk performance charts."""
        # Fragmentation data
        frag_report = get_fragmentation_report(self.disk)
        
        self.ax_frag.clear()
        metrics = ["Internal", "External"]
        values = [
            frag_report['internal_fragmentation'],
            frag_report['external_fragmentation']
        ]
        colors = ['#FF5722', '#FF9800']
        self.ax_frag.bar(metrics, values, color=colors)
        self.ax_frag.set_ylabel('Fragmentation %')
        self.ax_frag.set_title('Fragmentation Analysis')
        self.canvas_frag.draw()
        
        # Allocation method distribution
        self.ax_alloc.clear()
        method_stats = frag_report['allocation_stats']
        methods = [m.value.title() for m in method_stats.keys()]
        counts = [method_stats[m]['count'] for m in method_stats.keys()]
        colors = ['#2196F3', '#4CAF50', '#FF9800']
        self.ax_alloc.pie(counts, labels=methods, colors=colors, autopct='%1.0f%%')
        self.ax_alloc.set_title('File Allocation Methods')
        self.canvas_alloc.draw()
        
        # Update metrics table
        perf_metrics = calculate_metrics(self.disk)
        metrics_data = [
            ("Fragmentation", f"{frag_report['internal_fragmentation']:.2f}%"),
            ("Seek Time", str(perf_metrics['seek_time'])),
            ("Efficiency", f"{perf_metrics['efficiency']:.2f}%"),
            ("IOPS", f"{perf_metrics['iops']:.2f}"),
            ("Avg Response Time", f"{perf_metrics['avg_response_time_ms']:.2f} ms"),
            ("Disk Utilization", f"{perf_metrics['disk_utilization']:.2f}%"),
            ("Files", str(frag_report['file_count'])),
            ("Free Blocks", f"{frag_report['free_blocks']}/{frag_report['total_blocks']}")
        ]
        
        self.disk_metrics_table.setRowCount(len(metrics_data))
        for i, (metric, value) in enumerate(metrics_data):
            self.disk_metrics_table.setItem(i, 0, QTableWidgetItem(metric))
            self.disk_metrics_table.setItem(i, 1, QTableWidgetItem(value))

    def update_scheduling_charts(self):
        """Update scheduling comparison charts."""
        # Get request tracks
        tracks = [r.track for r in self.disk_scheduler.request_queue]
        
        if len(tracks) < 3:
            self.ax_sched.text(0.5, 0.5, 'Not enough requests\nfor comparison',
                             ha='center', va='center', transform=self.ax_sched.transAxes)
            self.canvas_sched.draw()
            return
        
        # Compare all algorithms
        results = compare_algorithms(tracks, 200)
        
        # Bar chart of seek times
        self.ax_sched.clear()
        algorithms = list(results.keys())
        seek_times = [results[a]['total_seek_time'] for a in algorithms]
        
        colors = plt.cm.Set3(np.linspace(0, 1, len(algorithms)))
        bars = self.ax_sched.bar(algorithms, seek_times, color=colors)
        
        # Highlight winner
        min_seek = min(seek_times)
        for bar, seek in zip(bars, seek_times):
            if seek == min_seek:
                bar.set_color('#4CAF50')
        
        self.ax_sched.set_ylabel('Total Seek Time')
        self.ax_sched.set_title('Disk Scheduling Algorithm Comparison')
        self.ax_sched.tick_params(axis='x', rotation=45)
        self.canvas_sched.draw()
        
        # Update comparison table
        self.sched_table.setRowCount(len(results))
        min_seek = min(r['total_seek_time'] for r in results.values())
        
        for i, (algo, stats) in enumerate(results.items()):
            is_winner = stats['total_seek_time'] == min_seek
            self.sched_table.setItem(i, 0, QTableWidgetItem(algo.upper()))
            self.sched_table.setItem(i, 1, QTableWidgetItem(str(stats['total_seek_time'])))
            self.sched_table.setItem(i, 2, QTableWidgetItem(f"{stats['avg_seek_time']:.1f}"))
            self.sched_table.setItem(i, 3, QTableWidgetItem(f"{stats['throughput']:.2f}"))
            winner_item = QTableWidgetItem("★" if is_winner else "")
            winner_item.setForeground(Qt.green if is_winner else Qt.black)
            self.sched_table.setItem(i, 4, winner_item)

    def update_memory_charts(self):
        """Update memory management charts."""
        # Simulate different page replacement algorithms
        access_sequence = list(range(20)) * 3  # Simulate pattern
        
        fault_counts = {}
        for algo in PageReplacementAlgorithm:
            mm = MemoryManager(
                physical_memory_size=4,
                virtual_memory_size=50,
                replacement_algorithm=algo
            )
            mm.create_page_table(1)
            
            for page in access_sequence:
                mm.access_page(1, page)
            
            fault_counts[algo.value] = mm.get_stats()['page_faults']
        
        # Bar chart
        self.ax_mem.clear()
        algorithms = list(fault_counts.keys())
        faults = list(fault_counts.values())
        
        colors = ['#FF5722' if f == max(faults) else '#4CAF50' if f == min(faults) else '#2196F3' 
                  for f in faults]
        self.ax_mem.bar(algorithms, faults, color=colors)
        self.ax_mem.set_ylabel('Page Faults')
        self.ax_mem.set_title('Page Replacement Algorithm Comparison\n(Lower is Better)')
        self.ax_mem.tick_params(axis='x', rotation=45)
        self.canvas_mem.draw()
        
        # Update stats
        stats = self.memory.get_stats()
        self.mem_stats_label.setText(
            f"Current Memory Stats:\n"
            f"Physical Frames: {stats['physical_frames']} | Used: {stats['used_frames']}\n"
            f"Page Faults: {stats['page_faults']} | Hits: {stats['page_hits']}\n"
            f"Fault Rate: {stats['page_fault_rate']:.2%} | "
            f"TLB Hit Rate: {stats['tlb_stats']['hit_rate']:.2%}"
        )

    def update_cache_charts(self):
        """Update cache performance charts."""
        # Simulate different cache policies
        access_pattern = list(range(30)) * 2
        
        hit_rates = {}
        for policy in CachePolicy:
            cache = DiskCache(capacity=8, policy=policy)
            
            for block in access_pattern:
                if cache.get(block) is None:
                    cache.put(block, f"data_{block}".encode())
            
            hit_rates[policy.value] = cache.get_stats()['hit_rate']
        
        # Bar chart
        self.ax_cache.clear()
        policies = [p.upper() for p in hit_rates.keys()]
        rates = list(hit_rates.values())
        
        colors = ['#4CAF50' if r == max(rates) else '#FF5722' if r == min(rates) else '#2196F3'
                  for r in rates]
        self.ax_cache.bar(policies, [r * 100 for r in rates], color=colors)
        self.ax_cache.set_ylabel('Hit Rate %')
        self.ax_cache.set_title('Cache Policy Comparison\n(Higher is Better)')
        self.canvas_cache.draw()
        
        # Update metrics table
        self.cache_metrics_table.setRowCount(len(hit_rates))
        for i, (policy, rate) in enumerate(hit_rates.items()):
            self.cache_metrics_table.setItem(i, 0, QTableWidgetItem(policy.upper()))
            self.cache_metrics_table.setItem(i, 1, QTableWidgetItem(f"{rate:.2%}"))
            self.cache_metrics_table.setItem(i, 2, QTableWidgetItem("N/A"))

    def update_raid_charts(self):
        """Update RAID performance charts."""
        # Compare RAID levels
        raid_stats = []
        for level in RAIDLevel:
            raid = RAIDArray(level, disk_size=100, num_disks=4)
            status = raid.get_status()
            usable_pct = (status['usable_capacity'] / 
                         (status['num_disks'] * status['disk_size'])) * 100
            raid_stats.append({
                'level': level.name.replace('RAID_', 'RAID '),
                'usable_pct': usable_pct,
                'redundancy': status['redundancy_disks']
            })

        # Bar chart
        self.ax_raid.clear()
        levels = [r['level'] for r in raid_stats]
        usable_pcts = [r['usable_pct'] for r in raid_stats]

        colors = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0']
        bars = self.ax_raid.bar(levels, usable_pcts, color=colors[:len(levels)])

        # Add redundancy indicators
        for bar, stat in zip(bars, raid_stats):
            height = bar.get_height()
            self.ax_raid.annotate(f"R:{stat['redundancy']}",
                                  xy=(bar.get_x() + bar.get_width() / 2, height),
                                  xytext=(0, 3),
                                  textcoords="offset points",
                                  ha='center', va='bottom')

        self.ax_raid.set_ylabel('Usable Capacity %')
        self.ax_raid.set_title('RAID Level Comparison\n(R=Redundancy Disks)')
        self.canvas_raid.draw()

        # Update RAID table
        self.raid_table.setRowCount(len(raid_stats))
        for i, stat in enumerate(raid_stats):
            self.raid_table.setItem(i, 0, QTableWidgetItem(stat['level']))
            self.raid_table.setItem(i, 1, QTableWidgetItem(f"{stat['usable_pct']:.1f}%"))
            self.raid_table.setItem(i, 2, QTableWidgetItem(str(stat['redundancy'])))
            perf = "High" if stat['usable_pct'] > 75 else "Medium" if stat['usable_pct'] > 50 else "Low"
            self.raid_table.setItem(i, 3, QTableWidgetItem(perf))

    def update_network_charts(self):
        """Update network I/O charts."""
        # Create interface and simulate traffic
        self.network.create_interface("eth0", "00:11:22:33:44:55", "192.168.1.1", 8080)

        # Simulate packet traffic
        packet_types = ['TCP', 'UDP', 'ICMP']
        packet_counts = [random.randint(50, 200) for _ in packet_types]

        # Bar chart
        self.ax_net.clear()
        colors = ['#2196F3', '#4CAF50', '#FF5722']
        bars = self.ax_net.bar(packet_types, packet_counts, color=colors)

        self.ax_net.set_ylabel('Packet Count')
        self.ax_net.set_title('Network Traffic by Protocol')
        self.canvas_net.draw()

        # Update network metrics
        net_stats = self.network.get_stats()
        self.net_metrics_label.setText(
            f"Total Packets: {net_stats['total_packets']}\n"
            f"TCP: {net_stats['tcp_packets']} | "
            f"UDP: {net_stats['udp_packets']} | "
            f"ICMP: {net_stats['icmp_packets']}\n"
            f"Interfaces: {len(net_stats['interfaces'])}\n"
            f"Active Sockets: {len(net_stats['sockets'])}"
        )

    def update_security_charts(self):
        """Update security audit charts."""
        # Get security stats
        sec_stats = self.security.get_stats()

        # Update security metrics label
        self.sec_label.setText(
            f"Users: {sec_stats['users']} | "
            f"Groups: {sec_stats['groups']} | "
            f"Active Sessions: {sec_stats['active_sessions']}\n"
            f"Current User: {sec_stats['current_user'] or 'None'}\n"
            f"Audit Entries: {sec_stats['audit_entries']}\n"
            f"Keys: {sec_stats['keys']} | "
            f"Capabilities: {sec_stats['capabilities_granted']}"
        )

        # Simulate audit log entries
        audit_entries = [
            ('2024-01-15 10:30', 'root', 'login', 'Success'),
            ('2024-01-15 10:35', 'user', 'file_access', 'Success'),
            ('2024-01-15 10:40', 'guest', 'login', 'Failed'),
            ('2024-01-15 11:00', 'user', 'process_create', 'Success'),
        ]

        self.audit_table.setRowCount(len(audit_entries))
        for i, (timestamp, user, action, status) in enumerate(audit_entries):
            self.audit_table.setItem(i, 0, QTableWidgetItem(timestamp))
            self.audit_table.setItem(i, 1, QTableWidgetItem(user))
            self.audit_table.setItem(i, 2, QTableWidgetItem(action))
            status_item = QTableWidgetItem(status)
            if status == 'Success':
                status_item.setForeground(Qt.green)
            else:
                status_item.setForeground(Qt.red)
            self.audit_table.setItem(i, 3, status_item)

    def update_overview(self):
        """Update system overview."""
        # Disk summary
        disk_stats = self.disk.get_stats()
        frag_report = get_fragmentation_report(self.disk)
        self.disk_summary.setText(
            f"Blocks: {disk_stats['used_blocks']}/{disk_stats['total_blocks']} used\n"
            f"Files: {disk_stats['file_count']}\n"
            f"Fragmentation: {frag_report['internal_fragmentation']:.1f}%\n"
            f"I/O Ops: {disk_stats['io_operations']}"
        )
        
        # Memory summary
        mem_stats = self.memory.get_stats()
        self.mem_summary.setText(
            f"Frames: {mem_stats['used_frames']}/{mem_stats['physical_frames']} used\n"
            f"Page Faults: {mem_stats['page_faults']}\n"
            f"Fault Rate: {mem_stats['page_fault_rate']:.2%}\n"
            f"Disk I/O: {mem_stats['disk_reads'] + mem_stats['disk_writes']}"
        )
        
        # Cache summary
        cache_stats = self.cache.get_stats()
        self.cache_summary.setText(
            f"Capacity: {cache_stats['capacity']} blocks\n"
            f"Used: {cache_stats['used']}\n"
            f"Hit Rate: {cache_stats['hit_rate']:.2%}\n"
            f"Evictions: {cache_stats['evictions']}"
        )
        
        # Process summary
        proc_stats = self.scheduler.get_statistics()
        self.proc_summary.setText(
            f"Processes: {proc_stats['total_processes']}\n"
            f"Completed: {proc_stats['completed']}\n"
            f"Avg Turnaround: {proc_stats['avg_turnaround']:.1f}ms\n"
            f"CPU Util: {proc_stats['cpu_utilization']:.1%}"
        )
        
        # Overall performance radar chart
        self.ax_perf.clear()
        
        categories = ['Disk\nEfficiency', 'Memory\nHit Rate', 'Cache\nHit Rate', 
                      'CPU\nUtilization', 'Scheduling\nEfficiency']
        
        # Normalize values to 0-100
        disk_eff = frag_report['used_blocks'] / frag_report['total_blocks'] * 100
        mem_hit = (1 - mem_stats['page_fault_rate']) * 100
        cache_hit = cache_stats['hit_rate'] * 100
        cpu_util = proc_stats['cpu_utilization'] * 100
        sched_eff = 80  # Estimated
        
        values = [disk_eff, mem_hit, cache_hit, cpu_util, sched_eff]
        
        # Create bar chart
        colors = ['#2196F3', '#4CAF50', '#FF9800', '#9C27B0', '#F44336']
        bars = self.ax_perf.bar(categories, values, color=colors)
        
        # Add value labels on bars
        for bar, val in zip(bars, values):
            height = bar.get_height()
            self.ax_perf.annotate(f'{val:.0f}',
                                  xy=(bar.get_x() + bar.get_width() / 2, height),
                                  xytext=(0, 3),
                                  textcoords="offset points",
                                  ha='center', va='bottom')
        
        self.ax_perf.set_ylim(0, 100)
        self.ax_perf.set_ylabel('Performance %')
        self.ax_perf.set_title('System Performance Overview')
        self.canvas_perf.draw()
