import random
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime


class AllocationMethod(Enum):
    """File allocation methods supported by the OS."""
    CONTIGUOUS = "contiguous"
    LINKED = "linked"
    INDEXED = "indexed"


@dataclass
class FileMetadata:
    """File metadata simulating inode structure."""
    name: str
    size: int
    created: datetime = field(default_factory=datetime.now)
    modified: datetime = field(default_factory=datetime.now)
    permissions: str = "rw-r--r--"
    owner: str = "user"
    group: str = "user"
    allocation_method: AllocationMethod = AllocationMethod.CONTIGUOUS
    index_block: Optional[int] = None


@dataclass
class DiskBlock:
    """Represents a single disk block with data and link."""
    data: Optional[str] = None
    next_block: Optional[int] = None
    is_index_block: bool = False
    index_pointers: List[int] = field(default_factory=list)


class Directory:
    """Directory structure for hierarchical file system."""
    
    def __init__(self, name: str, parent: Optional['Directory'] = None):
        self.name = name
        self.parent = parent
        self.files: Dict[str, FileMetadata] = {}
        self.subdirectories: Dict[str, 'Directory'] = {}
        self.created = datetime.now()
    
    def add_file(self, metadata: FileMetadata):
        self.files[metadata.name] = metadata
    
    def remove_file(self, name: str):
        if name in self.files:
            del self.files[name]
    
    def add_subdirectory(self, name: str) -> 'Directory':
        new_dir = Directory(name, self)
        self.subdirectories[name] = new_dir
        return new_dir
    
    def get_path(self) -> str:
        if self.parent is None:
            return "/"
        parent_path = self.parent.get_path()
        return f"{parent_path}{self.name}/" if parent_path != "/" else f"/{self.name}/"


class Disk:
    """
    Enhanced Disk model with OS file system features.
    Supports multiple allocation methods, directories, and I/O operations.
    """

    def __init__(self, size: int = 50, block_size: int = 4096):
        self.size = size
        self.block_size = block_size
        self.blocks: List[Optional[DiskBlock]] = [None] * size
        self.root_dir = Directory("root")
        self.current_dir = self.root_dir
        self.files: Dict[str, FileMetadata] = {}
        self.io_queue: List[Tuple[str, int, int]] = []  # (operation, block, size)
        self.total_io_operations = 0
        self.io_time_total = 0.0
        self.allocation_method = AllocationMethod.CONTIGUOUS
        
    def get_free_blocks(self) -> List[int]:
        """Return list of free block indices."""
        return [i for i, b in enumerate(self.blocks) if b is None]
    
    def get_free_count(self) -> int:
        """Return count of free blocks."""
        return sum(1 for b in self.blocks if b is None)
    
    def create_file(self, name: str, size_blocks: int, 
                    allocation: AllocationMethod = None) -> FileMetadata:
        """
        Create a file with specified allocation method.
        """
        if allocation is None:
            allocation = self.allocation_method
            
        if name in self.files:
            raise ValueError(f"File '{name}' already exists")
        
        free_blocks = self.get_free_blocks()
        if len(free_blocks) < size_blocks:
            raise ValueError(f"Not enough free space. Need {size_blocks}, have {len(free_blocks)}")
        
        metadata = FileMetadata(
            name=name, 
            size=size_blocks,
            allocation_method=allocation
        )
        
        if allocation == AllocationMethod.CONTIGUOUS:
            positions = self._allocate_contiguous(free_blocks, size_blocks)
        elif allocation == AllocationMethod.LINKED:
            positions = self._allocate_linked(free_blocks, size_blocks)
        elif allocation == AllocationMethod.INDEXED:
            positions = self._allocate_indexed(free_blocks, size_blocks)
            metadata.index_block = positions[0]
        else:
            positions = self._allocate_contiguous(free_blocks, size_blocks)
        
        # Mark blocks as used
        for pos in positions:
            self.blocks[pos] = DiskBlock(data=name)
        
        # Set up linked list for linked allocation
        if allocation == AllocationMethod.LINKED:
            for i in range(len(positions) - 1):
                self.blocks[positions[i]].next_block = positions[i + 1]
        
        # Set up index block for indexed allocation
        if allocation == AllocationMethod.INDEXED:
            self.blocks[positions[0]].is_index_block = True
            self.blocks[positions[0]].index_pointers = positions[1:]
        
        metadata.size = len(positions)
        self.files[name] = metadata
        self.current_dir.add_file(metadata)
        return metadata
    
    def _allocate_contiguous(self, free_blocks: List[int], size: int) -> List[int]:
        """Find contiguous space for file allocation."""
        if len(free_blocks) < size:
            raise ValueError("Not enough free space")
        
        # Try to find contiguous segment
        for i in range(len(free_blocks) - size + 1):
            segment = free_blocks[i:i + size]
            if segment == list(range(segment[0], segment[0] + size)):
                return segment
        
        # Fall back to random allocation (fragmented)
        return random.sample(free_blocks, size)
    
    def _allocate_linked(self, free_blocks: List[int], size: int) -> List[int]:
        """Allocate blocks for linked file structure."""
        return random.sample(free_blocks, size)
    
    def _allocate_indexed(self, free_blocks: List[int], size: int) -> List[int]:
        """Allocate index block + data blocks."""
        if len(free_blocks) < size + 1:
            raise ValueError("Not enough free space for indexed allocation")
        return random.sample(free_blocks, size + 1)
    
    def delete_file(self, name: str):
        """Delete file and free its blocks."""
        if name not in self.files:
            raise ValueError(f"File '{name}' not found")
        
        metadata = self.files[name]
        
        # Free all blocks allocated to this file
        if metadata.allocation_method == AllocationMethod.INDEXED and metadata.index_block is not None:
            # Free data blocks first
            for pos in self.blocks[metadata.index_block].index_pointers:
                self.blocks[pos] = None
            # Free index block
            self.blocks[metadata.index_block] = None
        else:
            for i, block in enumerate(self.blocks):
                if block and block.data == name:
                    self.blocks[i] = None
        
        del self.files[name]
        self.current_dir.remove_file(name)
    
    def get_file_blocks(self, name: str) -> List[int]:
        """Get all block indices for a file."""
        if name not in self.files:
            return []
        
        metadata = self.files[name]
        blocks = []
        
        if metadata.allocation_method == AllocationMethod.INDEXED and metadata.index_block is not None:
            blocks.append(metadata.index_block)
            blocks.extend(self.blocks[metadata.index_block].index_pointers)
        else:
            for i, block in enumerate(self.blocks):
                if block and block.data == name:
                    blocks.append(i)
        
        return blocks
    
    def read_block(self, block_num: int) -> Tuple[str, float]:
        """
        Simulate reading a disk block.
        Returns (data, io_time).
        """
        start_time = time.perf_counter()
        
        if block_num < 0 or block_num >= self.size:
            raise ValueError(f"Invalid block number: {block_num}")
        
        self.total_io_operations += 1
        
        # Simulate disk latency (2-10ms)
        latency = random.uniform(0.002, 0.01)
        time.sleep(latency / 1000)  # Scale down for simulation
        
        block = self.blocks[block_num]
        data = block.data if block else None
        
        io_time = time.perf_counter() - start_time
        self.io_time_total += io_time
        
        return data, io_time
    
    def write_block(self, block_num: int, data: str) -> float:
        """
        Simulate writing to a disk block.
        Returns io_time.
        """
        start_time = time.perf_counter()
        
        if block_num < 0 or block_num >= self.size:
            raise ValueError(f"Invalid block number: {block_num}")
        
        self.total_io_operations += 1
        
        # Simulate disk latency (2-10ms)
        latency = random.uniform(0.002, 0.01)
        time.sleep(latency / 1000)
        
        if self.blocks[block_num] is None:
            self.blocks[block_num] = DiskBlock()
        self.blocks[block_num].data = data
        
        io_time = time.perf_counter() - start_time
        self.io_time_total += io_time
        
        return io_time
    
    def read_file(self, name: str) -> Tuple[List[int], float]:
        """
        Read entire file and return (blocks_accessed, total_time).
        """
        blocks = self.get_file_blocks(name)
        total_time = 0.0
        
        for block_num in blocks:
            _, io_time = self.read_block(block_num)
            total_time += io_time
        
        return blocks, total_time
    
    def mkdir(self, name: str) -> Directory:
        """Create a new subdirectory."""
        if name in self.current_dir.subdirectories:
            raise ValueError(f"Directory '{name}' already exists")
        return self.current_dir.add_subdirectory(name)
    
    def cd(self, name: str):
        """Change current directory."""
        if name == "..":
            if self.current_dir.parent:
                self.current_dir = self.current_dir.parent
        elif name in self.current_dir.subdirectories:
            self.current_dir = self.current_dir.subdirectories[name]
        else:
            raise ValueError(f"Directory '{name}' not found")
    
    def ls(self) -> Tuple[List[str], List[str]]:
        """List current directory contents. Returns (files, directories)."""
        files = list(self.current_dir.files.keys())
        dirs = list(self.current_dir.subdirectories.keys())
        return files, dirs
    
    def pwd(self) -> str:
        """Print working directory."""
        return self.current_dir.get_path()
    
    def reset(self):
        """Reset disk to empty state."""
        self.blocks = [None] * self.size
        self.files = {}
        self.root_dir = Directory("root")
        self.current_dir = self.root_dir
        self.io_queue = []
        self.total_io_operations = 0
        self.io_time_total = 0.0

    def get_stats(self) -> dict:
        """Get disk statistics."""
        return {
            "total_blocks": self.size,
            "free_blocks": self.get_free_count(),
            "used_blocks": self.size - self.get_free_count(),
            "file_count": len(self.files),
            "io_operations": self.total_io_operations,
            "avg_io_time": self.io_time_total / max(1, self.total_io_operations)
        }
