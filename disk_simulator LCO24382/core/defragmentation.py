from typing import List, Tuple, Generator
from core.disk import Disk, DiskBlock, AllocationMethod


def defragment_basic(disk: Disk):
    """
    Sequential defragmentation: pack files in order of creation.
    Preserves file metadata and allocation method.
    """
    new_blocks: List[Optional[DiskBlock]] = [None] * disk.size
    pos = 0
    
    for name, metadata in list(disk.files.items()):
        blocks = disk.get_file_blocks(name)
        size = len(blocks)
        
        # Update file positions
        new_positions = []
        for i in range(size):
            new_blocks[pos] = DiskBlock(data=name)
            new_positions.append(pos)
            pos += 1
        
        # Update metadata
        if metadata.allocation_method == AllocationMethod.INDEXED and metadata.index_block is not None:
            # For indexed allocation, first block is index
            new_blocks[new_positions[0]].is_index_block = True
            new_blocks[new_positions[0]].index_pointers = new_positions[1:]
        
        elif metadata.allocation_method == AllocationMethod.LINKED:
            # For linked allocation, set up pointers
            for i in range(len(new_positions) - 1):
                new_blocks[new_positions[i]].next_block = new_positions[i + 1]
    
    disk.blocks = new_blocks


def defragment_optimized(disk: Disk):
    """
    Optimized defragmentation: sort files by size before packing.
    Larger files are placed first to reduce seek time.
    """
    new_blocks: List[Optional[DiskBlock]] = [None] * disk.size
    pos = 0
    
    # Sort files by size (descending)
    sorted_files = sorted(
        disk.files.items(),
        key=lambda x: len(disk.get_file_blocks(x[0])),
        reverse=True
    )
    
    for name, metadata in sorted_files:
        blocks = disk.get_file_blocks(name)
        size = len(blocks)
        
        new_positions = []
        for i in range(size):
            new_blocks[pos] = DiskBlock(data=name)
            new_positions.append(pos)
            pos += 1
        
        # Update metadata for specific allocation methods
        if metadata.allocation_method == AllocationMethod.INDEXED and metadata.index_block is not None:
            new_blocks[new_positions[0]].is_index_block = True
            new_blocks[new_positions[0]].index_pointers = new_positions[1:]
        
        elif metadata.allocation_method == AllocationMethod.LINKED:
            for i in range(len(new_positions) - 1):
                new_blocks[new_positions[i]].next_block = new_positions[i + 1]
    
    disk.blocks = new_blocks


def defragment_steps(disk: Disk) -> Generator[Tuple[int, int, str], None, None]:
    """
    Step-by-step defragmentation generator for animation.
    Yields (source_index, target_index, file_name).
    """
    pos = 0
    
    for name, metadata in disk.files.items():
        blocks = disk.get_file_blocks(name)
        sorted_positions = sorted(blocks)
        
        for old in sorted_positions:
            yield (old, pos, name)
            pos += 1


def defragment_by_method(disk: Disk, method: AllocationMethod):
    """
    Defragment files using a specific allocation method.
    """
    if method == AllocationMethod.CONTIGUOUS:
        defragment_contiguous(disk)
    elif method == AllocationMethod.LINKED:
        defragment_linked(disk)
    elif method == AllocationMethod.INDEXED:
        defragment_indexed(disk)


def defragment_contiguous(disk: Disk):
    """
    Defragment contiguously allocated files.
    """
    new_blocks: List[Optional[DiskBlock]] = [None] * disk.size
    pos = 0
    
    for name, metadata in disk.files.items():
        if metadata.allocation_method != AllocationMethod.CONTIGUOUS:
            continue
            
        blocks = disk.get_file_blocks(name)
        size = len(blocks)
        
        for i in range(size):
            new_blocks[pos] = DiskBlock(data=name)
            pos += 1
    
    disk.blocks = new_blocks


def defragment_linked(disk: Disk):
    """
    Defragment linked allocation files.
    """
    new_blocks: List[Optional[DiskBlock]] = [None] * disk.size
    pos = 0
    
    for name, metadata in disk.files.items():
        if metadata.allocation_method != AllocationMethod.LINKED:
            continue
            
        blocks = disk.get_file_blocks(name)
        size = len(blocks)
        
        new_positions = []
        for i in range(size):
            new_blocks[pos] = DiskBlock(data=name)
            new_positions.append(pos)
            pos += 1
        
        # Set up linked list pointers
        for i in range(len(new_positions) - 1):
            new_blocks[new_positions[i]].next_block = new_positions[i + 1]
    
    disk.blocks = new_blocks


def defragment_indexed(disk: Disk):
    """
    Defragment indexed allocation files.
    """
    new_blocks: List[Optional[DiskBlock]] = [None] * disk.size
    pos = 0
    
    for name, metadata in disk.files.items():
        if metadata.allocation_method != AllocationMethod.INDEXED:
            continue
            
        blocks = disk.get_file_blocks(name)
        size = len(blocks)
        
        new_positions = []
        for i in range(size):
            new_blocks[pos] = DiskBlock(data=name)
            new_positions.append(pos)
            pos += 1
        
        # First block is index block
        new_blocks[new_positions[0]].is_index_block = True
        new_blocks[new_positions[0]].index_pointers = new_positions[1:]
    
    disk.blocks = new_blocks


def analyze_defragmentation_impact(disk: Disk) -> dict:
    """
    Analyze the impact of defragmentation.
    """
    from core.performance import seek_time
    from core.fragmentation import fragmentation_level
    
    # Current metrics
    current_seek = seek_time(disk)
    current_frag = fragmentation_level(disk)
    
    return {
        "current_seek_time": current_seek,
        "current_fragmentation": current_frag,
        "estimated_improvement": current_frag * 0.8  # Estimated 80% improvement
    }
