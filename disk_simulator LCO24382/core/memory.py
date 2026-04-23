"""
Memory Management Module for OS Core.
Implements: Paging, Virtual Memory, Page Replacement Algorithms, TLB
"""

from enum import Enum
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import OrderedDict
import time
import random


class PageReplacementAlgorithm(Enum):
    """Page replacement algorithms."""
    FIFO = "fifo"
    LRU = "lru"
    OPTIMAL = "optimal"
    CLOCK = "clock"


@dataclass
class Page:
    """Represents a memory page."""
    page_number: int
    frame_number: int = -1
    valid: bool = False
    referenced: bool = False
    modified: bool = False
    last_access: float = 0.0
    load_time: float = 0.0


@dataclass
class PageTableEntry:
    """Page table entry with flags."""
    frame_number: int = -1
    valid: bool = False
    referenced: bool = False
    modified: bool = False
    protection: str = "rw"  # r, w, x combinations
    load_time: float = 0.0


@dataclass
class TLBEntry:
    """Translation Lookaside Buffer entry."""
    page_number: int
    frame_number: int
    valid: bool = True
    last_access: float = field(default_factory=time.time)


class TLB:
    """Translation Lookaside Buffer for fast address translation."""
    
    def __init__(self, size: int = 16):
        self.size = size
        self.entries: OrderedDict[int, TLBEntry] = OrderedDict()
        self.hits = 0
        self.misses = 0
    
    def lookup(self, page_number: int) -> Optional[int]:
        """Look up page number in TLB. Returns frame number or None."""
        if page_number in self.entries:
            entry = self.entries[page_number]
            entry.last_access = time.time()
            # Move to end (most recently used)
            self.entries.move_to_end(page_number)
            self.hits += 1
            return entry.frame_number
        self.misses += 1
        return None
    
    def add(self, page_number: int, frame_number: int):
        """Add entry to TLB."""
        if len(self.entries) >= self.size:
            # Remove oldest entry
            self.entries.popitem(last=False)
        
        self.entries[page_number] = TLBEntry(
            page_number=page_number,
            frame_number=frame_number
        )
    
    def invalidate(self, page_number: int):
        """Invalidate a TLB entry."""
        if page_number in self.entries:
            del self.entries[page_number]
    
    def flush(self):
        """Clear all TLB entries."""
        self.entries.clear()
    
    def get_stats(self) -> dict:
        """Get TLB statistics."""
        total = self.hits + self.misses
        return {
            "size": self.size,
            "entries_used": len(self.entries),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total if total > 0 else 0
        }


class MemoryManager:
    """
    Memory Manager with paging and virtual memory support.
    """
    
    def __init__(self, 
                 physical_memory_size: int = 64,  # Number of frames
                 virtual_memory_size: int = 256,   # Number of pages
                 page_size: int = 4096,             # Bytes per page
                 replacement_algorithm: PageReplacementAlgorithm = PageReplacementAlgorithm.LRU):
        
        self.physical_memory_size = physical_memory_size
        self.virtual_memory_size = virtual_memory_size
        self.page_size = page_size
        self.replacement_algorithm = replacement_algorithm
        
        # Physical memory (frames)
        self.frames: List[Optional[Page]] = [None] * physical_memory_size
        self.free_frames: Set[int] = set(range(physical_memory_size))
        
        # Page table for each process
        self.page_tables: Dict[int, Dict[int, PageTableEntry]] = {}
        
        # TLB
        self.tlb = TLB()
        
        # Page statistics
        self.page_faults = 0
        self.page_hits = 0
        self.disk_reads = 0
        self.disk_writes = 0
        
        # Clock algorithm hand
        self.clock_hand = 0
        
        # FIFO queue
        self.fifo_queue: List[Tuple[int, int]] = []  # (pid, page_num)
    
    def create_page_table(self, pid: int):
        """Create a new page table for a process."""
        self.page_tables[pid] = {}
    
    def allocate_page(self, pid: int, page_number: int) -> int:
        """
        Allocate a physical frame for a virtual page.
        Returns frame number. May trigger page replacement.
        """
        if pid not in self.page_tables:
            self.create_page_table(pid)
        
        # Check TLB first
        frame = self.tlb.lookup(page_number)
        if frame is not None:
            self.page_hits += 1
            return frame
        
        # Check page table
        pt = self.page_tables[pid]
        if page_number in pt and pt[page_number].valid:
            frame = pt[page_number].frame_number
            self.tlb.add(page_number, frame)
            self.page_hits += 1
            return frame
        
        # Page fault - need to load from disk
        self.page_faults += 1
        
        # Find or allocate a free frame
        if self.free_frames:
            frame = self.free_frames.pop()
        else:
            # Page replacement needed
            frame = self._replace_page(pid, page_number)
        
        # Set up page table entry
        pt[page_number] = PageTableEntry(
            frame_number=frame,
            valid=True,
            referenced=True,
            load_time=time.time()
        )
        
        # Create page in frame
        self.frames[frame] = Page(
            page_number=page_number,
            frame_number=frame,
            valid=True,
            load_time=time.time()
        )
        
        # Add to FIFO queue
        self.fifo_queue.append((pid, page_number))
        
        # Update TLB
        self.tlb.add(page_number, frame)
        
        self.disk_reads += 1
        
        return frame
    
    def _replace_page(self, pid: int, page_number: int) -> int:
        """
        Replace a page based on the selected algorithm.
        Returns the freed frame number.
        """
        if self.replacement_algorithm == PageReplacementAlgorithm.FIFO:
            return self._replace_fifo(pid, page_number)
        elif self.replacement_algorithm == PageReplacementAlgorithm.LRU:
            return self._replace_lru(pid, page_number)
        elif self.replacement_algorithm == PageReplacementAlgorithm.CLOCK:
            return self._replace_clock(pid, page_number)
        else:
            return self._replace_fifo(pid, page_number)
    
    def _replace_fifo(self, pid: int, page_number: int) -> int:
        """FIFO page replacement."""
        victim_pid, victim_page = self.fifo_queue.pop(0)
        pt = self.page_tables[victim_pid]
        frame = pt[victim_page].frame_number
        
        # Write back if modified
        if pt[victim_page].modified:
            self.disk_writes += 1
        
        # Mark as invalid
        pt[victim_page].valid = False
        self.tlb.invalidate(victim_page)
        
        return frame
    
    def _replace_lru(self, pid: int, page_number: int) -> int:
        """LRU page replacement."""
        # Find least recently used page
        lru_time = float('inf')
        victim_pid = None
        victim_page = None
        victim_frame = None
        
        for p, table in self.page_tables.items():
            for page_num, entry in table.items():
                if entry.valid and entry.last_access < lru_time:
                    lru_time = entry.last_access
                    victim_pid = p
                    victim_page = page_num
                    victim_frame = entry.frame_number
        
        if victim_frame is None:
            return 0
        
        pt = self.page_tables[victim_pid]
        
        # Write back if modified
        if pt[victim_page].modified:
            self.disk_writes += 1
        
        # Mark as invalid
        pt[victim_page].valid = False
        self.tlb.invalidate(victim_page)
        
        return victim_frame
    
    def _replace_clock(self, pid: int, page_number: int) -> int:
        """Clock (Second Chance) page replacement."""
        while True:
            frame = self.clock_hand
            page = self.frames[frame]
            
            if page is None:
                self.clock_hand = (self.clock_hand + 1) % self.physical_memory_size
                return frame
            
            # Find owner of this page
            for p, table in self.page_tables.items():
                if page.page_number in table:
                    entry = table[page.page_number]
                    if entry.referenced:
                        # Give second chance
                        entry.referenced = False
                    else:
                        # Replace this page
                        if entry.modified:
                            self.disk_writes += 1
                        entry.valid = False
                        self.tlb.invalidate(page.page_number)
                        self.clock_hand = (self.clock_hand + 1) % self.physical_memory_size
                        return frame
            
            self.clock_hand = (self.clock_hand + 1) % self.physical_memory_size
    
    def access_page(self, pid: int, page_number: int, write: bool = False) -> int:
        """
        Access a page (read or write).
        Returns physical frame number.
        """
        frame = self.allocate_page(pid, page_number)
        
        # Update access bits
        pt = self.page_tables[pid]
        entry = pt[page_number]
        entry.referenced = True
        entry.last_access = time.time()
        
        if write:
            entry.modified = True
        
        # Update page in frame
        if self.frames[frame]:
            self.frames[frame].referenced = True
            if write:
                self.frames[frame].modified = True
            self.frames[frame].last_access = time.time()
        
        return frame
    
    def translate_address(self, pid: int, virtual_address: int) -> Optional[int]:
        """
        Translate virtual address to physical address.
        Returns physical address or None if page fault.
        """
        page_number = virtual_address // self.page_size
        offset = virtual_address % self.page_size
        
        frame = self.access_page(pid, page_number)
        return frame * self.page_size + offset
    
    def deallocate_process(self, pid: int):
        """Deallocate all pages for a process."""
        if pid not in self.page_tables:
            return
        
        pt = self.page_tables[pid]
        for page_num, entry in pt.items():
            if entry.valid:
                frame = entry.frame_number
                self.frames[frame] = None
                self.free_frames.add(frame)
                self.tlb.invalidate(page_num)
                
                # Write back if modified
                if entry.modified:
                    self.disk_writes += 1
        
        del self.page_tables[pid]
        
        # Remove from FIFO queue
        self.fifo_queue = [(p, page) for p, page in self.fifo_queue if p != pid]
    
    def get_memory_map(self) -> List[Optional[Dict]]:
        """Get current memory map showing frame usage."""
        result = []
        for i, page in enumerate(self.frames):
            if page is None:
                result.append(None)
            else:
                # Find owning process
                owner = None
                for pid, pt in self.page_tables.items():
                    if page.page_number in pt and pt[page.page_number].valid:
                        owner = pid
                        break
                
                result.append({
                    "frame": i,
                    "page": page.page_number,
                    "process": owner,
                    "referenced": page.referenced,
                    "modified": page.modified
                })
        return result
    
    def get_stats(self) -> dict:
        """Get memory management statistics."""
        total_access = self.page_hits + self.page_faults
        return {
            "physical_frames": self.physical_memory_size,
            "virtual_pages": self.virtual_memory_size,
            "page_size": self.page_size,
            "free_frames": len(self.free_frames),
            "used_frames": self.physical_memory_size - len(self.free_frames),
            "page_hits": self.page_hits,
            "page_faults": self.page_faults,
            "page_fault_rate": self.page_faults / total_access if total_access > 0 else 0,
            "disk_reads": self.disk_reads,
            "disk_writes": self.disk_writes,
            "replacement_algorithm": self.replacement_algorithm.value,
            "tlb_stats": self.tlb.get_stats()
        }
    
    def reset(self):
        """Reset memory manager."""
        self.frames = [None] * self.physical_memory_size
        self.free_frames = set(range(self.physical_memory_size))
        self.page_tables = {}
        self.tlb = TLB(self.tlb.size)
        self.page_faults = 0
        self.page_hits = 0
        self.disk_reads = 0
        self.disk_writes = 0
        self.clock_hand = 0
        self.fifo_queue = []


class VirtualMemorySimulator:
    """
    Simulator for demonstrating virtual memory concepts.
    """
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager
        self.processes: Dict[int, Dict] = {}
    
    def create_process(self, pid: int, working_set_size: int):
        """Create a process with a working set of pages."""
        self.processes[pid] = {
            "working_set": random.sample(
                range(self.memory.virtual_memory_size), 
                min(working_set_size, self.memory.virtual_memory_size)
            ),
            "access_pattern": []
        }
        self.memory.create_page_table(pid)
    
    def simulate_access_pattern(self, pid: int, num_accesses: int = 100):
        """Simulate a pattern of memory accesses."""
        if pid not in self.processes:
            return
        
        process = self.processes[pid]
        working_set = process["working_set"]
        
        # 80% of accesses to 20% of pages (locality of reference)
        for _ in range(num_accesses):
            if random.random() < 0.8:
                # Access from working set
                page = random.choice(working_set[:len(working_set)//5])
            else:
                # Random access
                page = random.choice(working_set)
            
            self.memory.access_page(pid, page, write=random.random() < 0.3)
            process["access_pattern"].append(page)
    
    def get_working_set(self, pid: int, window_size: int = 10) -> Set[int]:
        """Get the working set for a process."""
        if pid not in self.processes:
            return set()
        
        pattern = self.processes[pid]["access_pattern"]
        if not pattern:
            return set()
        
        recent = pattern[-window_size:] if len(pattern) > window_size else pattern
        return set(recent)


# Example usage
if __name__ == "__main__":
    print("Memory Management Simulation")
    print("=" * 50)
    
    # Create memory manager
    mm = MemoryManager(
        physical_memory_size=4,
        virtual_memory_size=10,
        replacement_algorithm=PageReplacementAlgorithm.LRU
    )
    
    # Create process
    mm.create_page_table(1)
    
    # Access pages
    access_sequence = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
    print(f"\nPage access sequence: {access_sequence}")
    print(f"Physical frames: {mm.physical_memory_size}")
    print(f"Replacement algorithm: {mm.replacement_algorithm.value}")
    print()
    
    for page in access_sequence:
        frame = mm.access_page(1, page)
        stats = mm.get_stats()
        print(f"Access page {page} -> Frame {frame} | "
              f"Faults: {stats['page_faults']}, Hits: {stats['page_hits']}")
    
    print("\nFinal Statistics:")
    print(f"Page Fault Rate: {stats['page_fault_rate']:.2%}")
    print(f"TLB Hit Rate: {stats['tlb_stats']['hit_rate']:.2%}")
