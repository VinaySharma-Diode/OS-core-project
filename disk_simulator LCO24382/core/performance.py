from typing import Dict, List, Tuple
from core.disk import Disk


def seek_time(disk: Disk) -> int:
    """
    Calculate total seek time.
    Seek time is the sum of distances between consecutive blocks of each file.
    """
    total_time = 0
    
    for name, metadata in disk.files.items():
        blocks = disk.get_file_blocks(name)
        sorted_pos = sorted(blocks)
        for i in range(len(sorted_pos) - 1):
            total_time += abs(sorted_pos[i+1] - sorted_pos[i])
    
    return total_time


def efficiency(disk: Disk) -> float:
    """
    Calculate disk usage efficiency (% of used blocks).
    """
    used = disk.size - disk.get_free_count()
    return (used / disk.size) * 100 if disk.size else 0


def calculate_iops(disk: Disk, time_window: float = 1.0) -> float:
    """
    Calculate IOPS (I/O operations per second).
    """
    return disk.total_io_operations / time_window


def calculate_throughput(disk: Disk, time_window: float = 1.0) -> float:
    """
    Calculate throughput in MB/s.
    """
    bytes_transferred = disk.total_io_operations * disk.block_size
    return (bytes_transferred / (1024 * 1024)) / time_window


def average_response_time(disk: Disk) -> float:
    """
    Calculate average I/O response time.
    """
    if disk.total_io_operations == 0:
        return 0.0
    return disk.io_time_total / disk.total_io_operations * 1000  # ms


def disk_utilization(disk: Disk, time_window: float = 1.0) -> float:
    """
    Calculate disk utilization percentage.
    """
    busy_time = disk.io_time_total
    return min(100, (busy_time / time_window) * 100)


def file_access_patterns(disk: Disk) -> Dict[str, List[int]]:
    """
    Analyze file access patterns.
    Returns mapping of file names to their block sequences.
    """
    patterns = {}
    for name, metadata in disk.files.items():
        patterns[name] = disk.get_file_blocks(name)
    return patterns


def calculate_metrics(disk: Disk) -> Dict:
    """
    Calculate all performance metrics.
    """
    return {
        "seek_time": seek_time(disk),
        "efficiency": efficiency(disk),
        "iops": calculate_iops(disk),
        "throughput_mbps": calculate_throughput(disk),
        "avg_response_time_ms": average_response_time(disk),
        "disk_utilization": disk_utilization(disk),
        "io_operations": disk.total_io_operations,
        "avg_io_time": disk.io_time_total / max(1, disk.total_io_operations) * 1000
    }


def generate_performance_report(disk: Disk) -> Dict:
    """Generate comprehensive performance report."""
    stats = disk.get_stats()
    metrics = calculate_metrics(disk)
    
    return {
        "disk_stats": stats,
        "performance_metrics": metrics,
        "file_count": len(disk.files),
        "directory_path": disk.pwd()
    }
