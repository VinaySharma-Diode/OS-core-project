"""
Report generation utilities for OS Core Simulator.
"""

import csv
import json
from datetime import datetime
from typing import Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from core.disk import Disk
from core.fragmentation import fragmentation_level, get_fragmentation_report
from core.performance import calculate_metrics, generate_performance_report


def export_csv(disk: Disk, filename: str = "report.csv"):
    """
    Export disk state and performance metrics to CSV.
    """
    frag_report = get_fragmentation_report(disk)
    perf_metrics = calculate_metrics(disk)
    
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow(["OS Core Simulator - Disk Report"])
        writer.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow([])
        
        # Files section
        writer.writerow(["File", "Size (blocks)", "Allocation Method", "Block Positions"])
        for name, metadata in disk.files.items():
            blocks = disk.get_file_blocks(name)
            writer.writerow([
                name,
                metadata.size,
                metadata.allocation_method.value,
                str(blocks)
            ])
        
        writer.writerow([])
        
        # Performance metrics
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Fragmentation %", f"{frag_report['internal_fragmentation']:.2f}"])
        writer.writerow(["External Fragmentation %", f"{frag_report['external_fragmentation']:.2f}"])
        writer.writerow(["Seek Time", perf_metrics['seek_time']])
        writer.writerow(["Efficiency %", f"{perf_metrics['efficiency']:.2f}"])
        writer.writerow(["IOPS", f"{perf_metrics['iops']:.2f}"])
        writer.writerow(["Avg Response Time (ms)", f"{perf_metrics['avg_response_time_ms']:.2f}"])
        writer.writerow(["Disk Utilization %", f"{perf_metrics['disk_utilization']:.2f}"])
        
        writer.writerow([])
        
        # Allocation statistics
        writer.writerow(["Allocation Method Statistics"])
        writer.writerow(["Method", "Count", "Percentage"])
        for method, stats in frag_report['allocation_stats'].items():
            writer.writerow([
                method.value,
                stats['count'],
                f"{stats['percentage']:.1f}%"
            ])
        
        writer.writerow([])
        
        # Disk statistics
        writer.writerow(["Disk Statistics"])
        stats = disk.get_stats()
        for key, value in stats.items():
            writer.writerow([key, value])


def export_pdf(disk: Disk, filename: str = "report.pdf"):
    """
    Export disk state and performance metrics to PDF.
    """
    frag_report = get_fragmentation_report(disk)
    perf_metrics = calculate_metrics(disk)
    
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, "OS Core Simulator - Disk Report")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    y = height - 100
    
    # Files section
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Files")
    y -= 25
    
    c.setFont("Helvetica", 10)
    for name, metadata in disk.files.items():
        blocks = disk.get_file_blocks(name)
        c.drawString(50, y, f"{name}: {metadata.size} blocks ({metadata.allocation_method.value})")
        c.drawString(300, y, f"Blocks: {blocks}")
        y -= 15
        
        if y < 100:
            c.showPage()
            y = height - 50
    
    y -= 20
    
    # Performance metrics
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Performance Metrics")
    y -= 25
    
    c.setFont("Helvetica", 10)
    metrics = [
        ("Fragmentation", f"{frag_report['internal_fragmentation']:.2f}%"),
        ("External Fragmentation", f"{frag_report['external_fragmentation']:.2f}%"),
        ("Seek Time", str(perf_metrics['seek_time'])),
        ("Efficiency", f"{perf_metrics['efficiency']:.2f}%"),
        ("IOPS", f"{perf_metrics['iops']:.2f}"),
        ("Avg Response Time", f"{perf_metrics['avg_response_time_ms']:.2f} ms"),
        ("Disk Utilization", f"{perf_metrics['disk_utilization']:.2f}%"),
    ]
    
    for label, value in metrics:
        c.drawString(50, y, f"{label}:")
        c.drawString(200, y, value)
        y -= 15
    
    y -= 10
    
    # Allocation statistics
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Allocation Method Distribution")
    y -= 25
    
    c.setFont("Helvetica", 10)
    for method, stats in frag_report['allocation_stats'].items():
        c.drawString(50, y, f"{method.value.title()}:")
        c.drawString(200, y, f"{stats['count']} files ({stats['percentage']:.1f}%)")
        y -= 15
    
    # Disk stats
    y -= 10
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Disk Statistics")
    y -= 25
    
    c.setFont("Helvetica", 10)
    stats = disk.get_stats()
    c.drawString(50, y, f"Total Blocks: {stats['total_blocks']}")
    y -= 15
    c.drawString(50, y, f"Used Blocks: {stats['used_blocks']}")
    y -= 15
    c.drawString(50, y, f"Free Blocks: {stats['free_blocks']}")
    y -= 15
    c.drawString(50, y, f"File Count: {stats['file_count']}")
    y -= 15
    c.drawString(50, y, f"I/O Operations: {stats['io_operations']}")
    
    c.save()


def export_json(disk: Disk, filename: str = "report.json"):
    """
    Export comprehensive report to JSON.
    """
    report = {
        "generated": datetime.now().isoformat(),
        "disk": {
            "stats": disk.get_stats(),
            "files": {
                name: {
                    "size": meta.size,
                    "method": meta.allocation_method.value,
                    "blocks": disk.get_file_blocks(name)
                }
                for name, meta in disk.files.items()
            }
        },
        "fragmentation": get_fragmentation_report(disk),
        "performance": calculate_metrics(disk)
    }
    
    with open(filename, "w") as f:
        json.dump(report, f, indent=2, default=str)


def generate_summary(disk: Disk) -> str:
    """
    Generate a text summary of disk state.
    """
    frag_report = get_fragmentation_report(disk)
    perf_metrics = calculate_metrics(disk)
    stats = disk.get_stats()
    
    summary = f"""
OS Core Simulator - Disk Summary
================================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Disk Statistics:
- Total Blocks: {stats['total_blocks']}
- Used Blocks: {stats['used_blocks']}
- Free Blocks: {stats['free_blocks']}
- Files: {stats['file_count']}
- I/O Operations: {stats['io_operations']}

Performance Metrics:
- Fragmentation: {frag_report['internal_fragmentation']:.2f}%
- External Fragmentation: {frag_report['external_fragmentation']:.2f}%
- Seek Time: {perf_metrics['seek_time']}
- Efficiency: {perf_metrics['efficiency']:.2f}%
- IOPS: {perf_metrics['iops']:.2f}
- Avg Response Time: {perf_metrics['avg_response_time_ms']:.2f} ms

Allocation Methods:
"""
    for method, method_stats in frag_report['allocation_stats'].items():
        summary += f"- {method.value.title()}: {method_stats['count']} files ({method_stats['percentage']:.1f}%)\n"
    
    return summary
