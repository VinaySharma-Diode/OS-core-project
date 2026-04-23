from typing import List
from core.disk import Disk, AllocationMethod


def fragmentation_level(disk: Disk) -> float:
    """
    Calculate fragmentation percentage.
    A file is fragmented if its blocks are not contiguous.
    """
    fragmented = 0
    total = 0
    
    for name, metadata in disk.files.items():
        blocks = disk.get_file_blocks(name)
        total += len(blocks)
        sorted_pos = sorted(blocks)
        
        for i in range(len(sorted_pos) - 1):
            if sorted_pos[i+1] != sorted_pos[i] + 1:
                fragmented += 1
    
    return (fragmented / total) * 100 if total else 0


def external_fragmentation(disk: Disk) -> float:
    """
    Calculate external fragmentation - wasted space between allocated blocks.
    """
    free_blocks = disk.get_free_blocks()
    if not free_blocks:
        return 0.0
    
    # Count contiguous free segments
    segments = 1
    for i in range(1, len(free_blocks)):
        if free_blocks[i] != free_blocks[i-1] + 1:
            segments += 1
    
    # Fragmentation is high when there are many small free segments
    return (segments / len(free_blocks)) * 100


def allocation_efficiency(disk: Disk) -> dict:
    """
    Calculate allocation efficiency metrics by method.
    """
    stats = {
        AllocationMethod.CONTIGUOUS: {"count": 0, "avg_fragmentation": 0},
        AllocationMethod.LINKED: {"count": 0, "avg_fragmentation": 0},
        AllocationMethod.INDEXED: {"count": 0, "avg_fragmentation": 0}
    }
    
    for name, metadata in disk.files.items():
        method = metadata.allocation_method
        stats[method]["count"] += 1
    
    total = len(disk.files)
    for method in stats:
        count = stats[method]["count"]
        stats[method]["percentage"] = (count / total * 100) if total > 0 else 0
    
    return stats


def get_fragmentation_report(disk: Disk) -> dict:
    """Generate comprehensive fragmentation report."""
    return {
        "internal_fragmentation": fragmentation_level(disk),
        "external_fragmentation": external_fragmentation(disk),
        "allocation_stats": allocation_efficiency(disk),
        "free_blocks": disk.get_free_count(),
        "total_blocks": disk.size,
        "used_blocks": disk.size - disk.get_free_count(),
        "file_count": len(disk.files)
    }
