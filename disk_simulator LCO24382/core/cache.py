"""
Cache Management Module for OS Core.
Implements: Disk Cache, Buffer Cache with LRU, LFU, FIFO policies
"""

from enum import Enum
from typing import Dict, Optional, List, Tuple, OrderedDict
from dataclasses import dataclass, field
from collections import OrderedDict, defaultdict
import time
import hashlib


class CachePolicy(Enum):
    """Cache replacement policies."""
    LRU = "lru"          # Least Recently Used
    LFU = "lfu"          # Least Frequently Used
    FIFO = "fifo"        # First In First Out
    MRU = "mru"          # Most Recently Used


@dataclass
class CacheBlock:
    """Represents a cached disk block."""
    block_id: int
    data: bytes
    dirty: bool = False  # Modified since load
    load_time: float = field(default_factory=time.time)
    last_access: float = field(default_factory=time.time)
    access_count: int = 0
    
    def __repr__(self):
        return f"CacheBlock({self.block_id}, dirty={self.dirty}, count={self.access_count})"


class DiskCache:
    """
    Disk Buffer Cache with configurable replacement policy.
    """
    
    def __init__(self, capacity: int = 64, policy: CachePolicy = CachePolicy.LRU):
        self.capacity = capacity
        self.policy = policy
        self.cache: OrderedDict[int, CacheBlock] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.writes = 0
        self.reads = 0
        self.evictions = 0
        self.dirty_evictions = 0
        
        # Statistics
        self.total_hit_time = 0.0  # Time saved by hits
        self.total_miss_penalty = 0.0
    
    def get(self, block_id: int) -> Optional[bytes]:
        """
        Read from cache. Returns data or None if miss.
        """
        if block_id in self.cache:
            block = self.cache[block_id]
            block.last_access = time.time()
            block.access_count += 1
            self.hits += 1
            self.reads += 1
            
            # Move to end (most recent) for LRU
            if self.policy == CachePolicy.LRU:
                self.cache.move_to_end(block_id)
            
            return block.data
        
        self.misses += 1
        return None
    
    def put(self, block_id: int, data: bytes, dirty: bool = False):
        """
        Write to cache. May trigger eviction.
        """
        if block_id in self.cache:
            # Update existing block
            block = self.cache[block_id]
            block.data = data
            block.dirty = dirty
            block.last_access = time.time()
            block.access_count += 1
            
            if self.policy == CachePolicy.LRU:
                self.cache.move_to_end(block_id)
        else:
            # New block - check for eviction
            if len(self.cache) >= self.capacity:
                self._evict()
            
            # Add new block
            block = CacheBlock(
                block_id=block_id,
                data=data,
                dirty=dirty
            )
            self.cache[block_id] = block
            
            if self.policy == CachePolicy.FIFO:
                # Keep insertion order
                pass
        
        if dirty:
            self.writes += 1
        else:
            self.reads += 1
    
    def _evict(self):
        """Evict a block based on cache policy."""
        if not self.cache:
            return
        
        victim_id = None
        
        if self.policy == CachePolicy.LRU:
            # Remove least recently used (first item)
            victim_id = next(iter(self.cache))
        
        elif self.policy == CachePolicy.MRU:
            # Remove most recently used (last item)
            victim_id = next(reversed(self.cache))
        
        elif self.policy == CachePolicy.LFU:
            # Remove least frequently used
            victim_id = min(self.cache.keys(), 
                          key=lambda k: self.cache[k].access_count)
        
        elif self.policy == CachePolicy.FIFO:
            # Remove oldest (first inserted)
            victim_id = next(iter(self.cache))
        
        if victim_id is not None:
            block = self.cache[victim_id]
            if block.dirty:
                self.dirty_evictions += 1
            self.cache.pop(victim_id)
            self.evictions += 1
    
    def flush(self, block_id: Optional[int] = None) -> List[int]:
        """
        Flush dirty blocks to disk.
        Returns list of flushed block IDs.
        """
        flushed = []
        
        if block_id is not None:
            if block_id in self.cache and self.cache[block_id].dirty:
                self.cache[block_id].dirty = False
                flushed.append(block_id)
        else:
            # Flush all dirty blocks
            for bid, block in list(self.cache.items()):
                if block.dirty:
                    block.dirty = False
                    flushed.append(bid)
        
        return flushed
    
    def invalidate(self, block_id: Optional[int] = None):
        """Invalidate cache entries."""
        if block_id is not None:
            if block_id in self.cache:
                del self.cache[block_id]
        else:
            # Flush dirty blocks first
            self.flush()
            self.cache.clear()
    
    def get_cache_contents(self) -> List[Dict]:
        """Get current cache contents for visualization."""
        return [
            {
                "block_id": bid,
                "size": len(block.data),
                "dirty": block.dirty,
                "access_count": block.access_count,
                "age": time.time() - block.load_time,
                "last_access": time.time() - block.last_access
            }
            for bid, block in self.cache.items()
        ]
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        total_access = self.hits + self.misses
        return {
            "capacity": self.capacity,
            "used": len(self.cache),
            "policy": self.policy.value,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total_access if total_access > 0 else 0,
            "miss_rate": self.misses / total_access if total_access > 0 else 0,
            "reads": self.reads,
            "writes": self.writes,
            "evictions": self.evictions,
            "dirty_evictions": self.dirty_evictions
        }
    
    def reset(self):
        """Reset cache state."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        self.writes = 0
        self.reads = 0
        self.evictions = 0
        self.dirty_evictions = 0


class TwoLevelCache:
    """
    Two-level cache system (L1 and L2).
    L1: Smaller, faster cache
    L2: Larger, slower cache
    """
    
    def __init__(self, l1_capacity: int = 16, l2_capacity: int = 64):
        self.l1 = DiskCache(l1_capacity, CachePolicy.LRU)
        self.l2 = DiskCache(l2_capacity, CachePolicy.LRU)
        self.l1_time = 0.001   # 1 microsecond
        self.l2_time = 0.01    # 10 microseconds
        self.disk_time = 10.0  # 10 milliseconds
    
    def get(self, block_id: int) -> Tuple[Optional[bytes], str, float]:
        """
        Get data from cache hierarchy.
        Returns (data, cache_level, access_time).
        """
        # Try L1 first
        data = self.l1.get(block_id)
        if data is not None:
            return data, "L1", self.l1_time
        
        # Try L2
        data = self.l2.get(block_id)
        if data is not None:
            # Promote to L1
            self.l1.put(block_id, data)
            return data, "L2", self.l2_time
        
        # Miss - would need to fetch from disk
        return None, "DISK", self.disk_time
    
    def put(self, block_id: int, data: bytes, dirty: bool = False):
        """Write data to cache (write-through to L2)."""
        self.l1.put(block_id, data, dirty)
        self.l2.put(block_id, data, dirty)
    
    def get_stats(self) -> dict:
        """Get combined cache statistics."""
        l1_stats = self.l1.get_stats()
        l2_stats = self.l2.get_stats()
        
        # Calculate effective hit rate
        total_l1_access = l1_stats["hits"] + l1_stats["misses"]
        total_l2_access = l2_stats["hits"] + l2_stats["misses"]
        
        if total_l1_access == 0:
            effective_hit_rate = 0
        else:
            l1_hit_rate = l1_stats["hits"] / total_l1_access
            l2_hit_rate = l2_stats["hits"] / total_l1_access  # L2 hits are L1 misses
            effective_hit_rate = l1_hit_rate + l2_hit_rate
        
        return {
            "l1": l1_stats,
            "l2": l2_stats,
            "effective_hit_rate": effective_hit_rate,
            "l1_hit_rate": l1_stats["hit_rate"],
            "l2_hit_rate": l2_stats["hit_rate"]
        }
    
    def reset(self):
        """Reset both cache levels."""
        self.l1.reset()
        self.l2.reset()


class WritePolicy(Enum):
    """Write policies for cache."""
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"


class BufferedIO:
    """
    Buffered I/O operations for efficient disk access.
    """
    
    def __init__(self, cache: DiskCache, write_policy: WritePolicy = WritePolicy.WRITE_BACK):
        self.cache = cache
        self.write_policy = write_policy
        self.read_buffer_size = 4096
        self.write_buffer: List[Tuple[int, bytes]] = []
        self.write_buffer_limit = 10
    
    def read(self, block_id: int) -> bytes:
        """Read a block with buffering."""
        data = self.cache.get(block_id)
        if data is not None:
            return data
        
        # Cache miss - would read from disk
        # For simulation, return dummy data
        data = b"\x00" * self.read_buffer_size
        self.cache.put(block_id, data)
        return data
    
    def write(self, block_id: int, data: bytes):
        """Write a block with buffering."""
        if self.write_policy == WritePolicy.WRITE_THROUGH:
            # Write to cache and immediately mark dirty
            self.cache.put(block_id, data, dirty=True)
            # Would also write to disk immediately
        else:  # WRITE_BACK
            self.cache.put(block_id, data, dirty=True)
            # Delayed write to disk
    
    def flush_writes(self):
        """Flush all dirty blocks to disk."""
        flushed = self.cache.flush()
        return flushed
    
    def get_stats(self) -> dict:
        """Get I/O statistics."""
        return {
            "write_policy": self.write_policy.value,
            "cache_stats": self.cache.get_stats()
        }


# Example usage
if __name__ == "__main__":
    print("Cache Management Simulation")
    print("=" * 50)
    
    # Create cache
    cache = DiskCache(capacity=4, policy=CachePolicy.LRU)
    
    # Simulate access pattern
    access_pattern = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
    
    print(f"\nCache capacity: {cache.capacity}")
    print(f"Replacement policy: {cache.policy.value}")
    print(f"Access pattern: {access_pattern}")
    print()
    
    for block_id in access_pattern:
        # Simulate read
        data = cache.get(block_id)
        if data is None:
            print(f"Block {block_id}: MISS - Loading from disk")
            # Load from "disk"
            cache.put(block_id, f"data_{block_id}".encode())
        else:
            print(f"Block {block_id}: HIT")
    
    print(f"\nFinal Statistics:")
    stats = cache.get_stats()
    print(f"Hit Rate: {stats['hit_rate']:.2%}")
    print(f"Miss Rate: {stats['miss_rate']:.2%}")
    print(f"Evictions: {stats['evictions']}")
    
    # Test two-level cache
    print("\n" + "=" * 50)
    print("Two-Level Cache Test")
    print("=" * 50)
    
    two_level = TwoLevelCache(l1_capacity=2, l2_capacity=4)
    
    for block_id in access_pattern:
        data, level, access_time = two_level.get(block_id)
        if data is None:
            print(f"Block {block_id}: {level} MISS ({access_time}ms)")
            two_level.put(block_id, f"data_{block_id}".encode())
        else:
            print(f"Block {block_id}: {level} HIT ({access_time}ms)")
    
    stats = two_level.get_stats()
    print(f"\nL1 Hit Rate: {stats['l1_hit_rate']:.2%}")
    print(f"L2 Hit Rate: {stats['l2_hit_rate']:.2%}")
    print(f"Effective Hit Rate: {stats['effective_hit_rate']:.2%}")
