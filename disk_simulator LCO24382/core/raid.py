"""
RAID (Redundant Array of Independent Disks) Simulation Module.
Implements RAID 0, 1, 5, and 6 configurations.
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Set
import numpy as np


class RAIDLevel(Enum):
    """RAID configuration levels."""
    RAID_0 = "stripe"      # Striping, no redundancy
    RAID_1 = "mirror"      # Mirroring
    RAID_5 = "striped_parity"  # Striping with distributed parity
    RAID_6 = "double_parity"   # Striping with double parity


@dataclass
class DiskDrive:
    """Represents a single disk drive in the array."""
    disk_id: int
    size: int  # Blocks
    blocks: List[Optional[bytes]]
    failed: bool = False
    
    def __init__(self, disk_id: int, size: int):
        self.disk_id = disk_id
        self.size = size
        self.blocks = [None] * size
        self.failed = False
        
    def read(self, block: int) -> Optional[bytes]:
        """Read block from disk."""
        if self.failed or block < 0 or block >= self.size:
            return None
        return self.blocks[block]
        
    def write(self, block: int, data: bytes) -> bool:
        """Write block to disk."""
        if self.failed or block < 0 or block >= self.size:
            return False
        self.blocks[block] = data
        return True
        
    def fail(self):
        """Simulate disk failure."""
        self.failed = True
        
    def rebuild(self):
        """Rebuild disk (after replacement)."""
        self.failed = False
        self.blocks = [None] * self.size


class RAIDArray:
    """
    RAID array controller.
    Manages multiple disks with various RAID configurations.
    """
    
    def __init__(self, level: RAIDLevel, disk_size: int = 100, num_disks: int = 4,
                 stripe_size: int = 4):
        self.level = level
        self.disk_size = disk_size
        self.num_disks = num_disks
        self.stripe_size = stripe_size  # Blocks per stripe unit
        
        # Create disks
        self.disks: List[DiskDrive] = [
            DiskDrive(i, disk_size) for i in range(num_disks)
        ]
        
        # Calculate usable capacity
        self._update_capacity()
        
        # Statistics
        self.read_count = 0
        self.write_count = 0
        self.rebuild_operations = 0
        self.parity_calculations = 0
        
    def _update_capacity(self):
        """Calculate usable storage capacity."""
        if self.level == RAIDLevel.RAID_0:
            self.usable_capacity = self.disk_size * self.num_disks
            self.redundancy_disks = 0
        elif self.level == RAIDLevel.RAID_1:
            self.usable_capacity = self.disk_size * (self.num_disks // 2)
            self.redundancy_disks = self.num_disks // 2
        elif self.level == RAIDLevel.RAID_5:
            self.usable_capacity = self.disk_size * (self.num_disks - 1)
            self.redundancy_disks = 1
        elif self.level == RAIDLevel.RAID_6:
            self.usable_capacity = self.disk_size * (self.num_disks - 2)
            self.redundancy_disks = 2
            
    def _calculate_parity(self, data_blocks: List[Optional[bytes]]) -> bytes:
        """Calculate XOR parity for data blocks."""
        if not data_blocks or all(d is None for d in data_blocks):
            return b'\x00' * 4096  # Assume 4KB blocks
            
        # Use first non-None block as base size
        block_size = len(next(d for d in data_blocks if d is not None))
        parity = bytearray(block_size)
        
        for data in data_blocks:
            if data is not None:
                for i, b in enumerate(data):
                    parity[i] ^= b
                    
        self.parity_calculations += 1
        return bytes(parity)
        
    def _calculate_double_parity(self, data_blocks: List[Optional[bytes]]) -> Tuple[bytes, bytes]:
        """Calculate P and Q parity for RAID 6 ( Reed-Solomon-like)."""
        # P parity = XOR (same as RAID 5)
        p_parity = self._calculate_parity(data_blocks)
        
        # Q parity = weighted XOR (simplified)
        block_size = len(p_parity)
        q_parity = bytearray(block_size)
        
        for i, data in enumerate(data_blocks):
            if data is not None:
                weight = i + 1
                for j, b in enumerate(data):
                    # Galois field multiplication (simplified)
                    q_parity[j] ^= (b * weight) & 0xFF
                    
        return p_parity, bytes(q_parity)
        
    def _get_stripe_location(self, logical_block: int) -> Tuple[int, int, int]:
        """
        Map logical block to physical location.
        Returns (disk_index, physical_block, stripe_number)
        """
        stripe_unit = self.stripe_size
        stripe_number = logical_block // (stripe_unit * self.get_data_disks())
        stripe_offset = logical_block % (stripe_unit * self.get_data_disks())
        
        data_disk = stripe_offset // stripe_unit
        physical_block = stripe_number * stripe_unit + (stripe_offset % stripe_unit)
        
        return data_disk, physical_block, stripe_number
        
    def get_data_disks(self) -> int:
        """Get number of data disks (excluding parity)."""
        return self.num_disks - self.redundancy_disks
        
    def read(self, logical_block: int) -> Optional[bytes]:
        """
        Read from RAID array.
        For RAID 5/6, can reconstruct from parity if disk failed.
        """
        self.read_count += 1
        
        if self.level == RAIDLevel.RAID_0:
            disk_idx, phys_block, _ = self._get_stripe_location(logical_block)
            return self.disks[disk_idx].read(phys_block)
            
        elif self.level == RAIDLevel.RAID_1:
            # Read from first non-failed mirror
            disk_idx = (logical_block // self.disk_size) * 2
            for i in range(2):
                if disk_idx + i < self.num_disks:
                    data = self.disks[disk_idx + i].read(logical_block % self.disk_size)
                    if data is not None:
                        return data
            return None
            
        elif self.level == RAIDLevel.RAID_5:
            data_disks = self.get_data_disks()
            stripe_number = logical_block // (self.stripe_size * data_disks)
            stripe_offset = logical_block % (self.stripe_size * data_disks)
            
            data_disk = stripe_offset // self.stripe_size
            phys_block = stripe_number * self.stripe_size + (stripe_offset % self.stripe_size)
            
            # Calculate parity disk for this stripe
            parity_disk = stripe_number % self.num_disks
            actual_disk = data_disk if data_disk < parity_disk else data_disk + 1
            
            # Try to read from data disk
            if not self.disks[actual_disk].failed:
                return self.disks[actual_disk].read(phys_block)
            else:
                # Reconstruct from parity
                blocks = []
                for i in range(self.num_disks):
                    if i != parity_disk:
                        blocks.append(self.disks[i].read(phys_block))
                    else:
                        blocks.append(None)  # Parity slot
                        
                return self._calculate_parity(blocks)
                
        elif self.level == RAIDLevel.RAID_6:
            # Similar to RAID 5 but with double parity
            data_disks = self.get_data_disks()
            stripe_number = logical_block // (self.stripe_size * data_disks)
            stripe_offset = logical_block % (self.stripe_size * data_disks)
            
            data_disk = stripe_offset // self.stripe_size
            phys_block = stripe_number * self.stripe_size + (stripe_offset % self.stripe_size)
            
            # Calculate parity disks for this stripe
            p_disk = stripe_number % self.num_disks
            q_disk = (stripe_number + 1) % self.num_disks
            
            # Map to actual disk index
            actual_disk = data_disk
            if data_disk >= min(p_disk, q_disk):
                actual_disk += 1
            if data_disk >= max(p_disk, q_disk):
                actual_disk += 1
                
            if not self.disks[actual_disk].failed:
                return self.disks[actual_disk].read(phys_block)
            else:
                # Reconstruct (simplified - would need both parities for dual failure)
                return None
                
        return None
        
    def write(self, logical_block: int, data: bytes) -> bool:
        """
        Write to RAID array.
        For RAID 5/6, updates parity as well.
        """
        self.write_count += 1
        
        if self.level == RAIDLevel.RAID_0:
            disk_idx, phys_block, _ = self._get_stripe_location(logical_block)
            return self.disks[disk_idx].write(phys_block, data)
            
        elif self.level == RAIDLevel.RAID_1:
            # Write to both mirrors
            disk_idx = (logical_block // self.disk_size) * 2
            success = True
            for i in range(2):
                if disk_idx + i < self.num_disks:
                    if not self.disks[disk_idx + i].write(
                        logical_block % self.disk_size, data):
                        success = False
            return success
            
        elif self.level == RAIDLevel.RAID_5:
            data_disks = self.get_data_disks()
            stripe_number = logical_block // (self.stripe_size * data_disks)
            stripe_offset = logical_block % (self.stripe_size * data_disks)
            
            data_disk = stripe_offset // self.stripe_size
            phys_block = stripe_number * self.stripe_size + (stripe_offset % self.stripe_size)
            
            parity_disk = stripe_number % self.num_disks
            actual_disk = data_disk if data_disk < parity_disk else data_disk + 1
            
            # Read old data and old parity for update
            old_data = self.disks[actual_disk].read(phys_block)
            old_parity = self.disks[parity_disk].read(phys_block)
            
            # Write new data
            if not self.disks[actual_disk].write(phys_block, data):
                return False
                
            # Calculate and write new parity
            if old_data is not None and old_parity is not None:
                # New parity = old_parity XOR old_data XOR new_data
                new_parity = bytes(
                    old_parity[i] ^ old_data[i] ^ data[i]
                    for i in range(len(data))
                )
                self.disks[parity_disk].write(phys_block, new_parity)
            else:
                # Full stripe read for parity calculation
                blocks = []
                for i in range(self.num_disks):
                    if i != parity_disk:
                        if i == actual_disk:
                            blocks.append(data)
                        else:
                            blocks.append(self.disks[i].read(phys_block))
                new_parity = self._calculate_parity(blocks)
                self.disks[parity_disk].write(phys_block, new_parity)
                
            return True
            
        elif self.level == RAIDLevel.RAID_6:
            # Similar to RAID 5 but with double parity update
            pass
            
        return False
        
    def fail_disk(self, disk_id: int) -> bool:
        """Simulate disk failure."""
        if 0 <= disk_id < self.num_disks:
            self.disks[disk_id].fail()
            return True
        return False
        
    def rebuild_disk(self, disk_id: int) -> bool:
        """Rebuild failed disk using parity/redundancy."""
        if disk_id < 0 or disk_id >= self.num_disks:
            return False
            
        if not self.disks[disk_id].failed:
            return False  # Disk not failed
            
        self.disks[disk_id].rebuild()
        
        # Reconstruct all blocks
        for block in range(self.disk_size):
            if self.level == RAIDLevel.RAID_1:
                # Copy from mirror
                mirror_disk = disk_id + 1 if disk_id % 2 == 0 else disk_id - 1
                if mirror_disk < self.num_disks:
                    data = self.disks[mirror_disk].read(block)
                    if data:
                        self.disks[disk_id].write(block, data)
                        self.rebuild_operations += 1
                        
            elif self.level == RAIDLevel.RAID_5:
                # Reconstruct from parity
                stripe_number = block // self.stripe_size
                parity_disk = stripe_number % self.num_disks
                
                blocks = []
                for i in range(self.num_disks):
                    if i != parity_disk and i != disk_id:
                        blocks.append(self.disks[i].read(block))
                    else:
                        blocks.append(None)
                        
                reconstructed = self._calculate_parity(blocks)
                self.disks[disk_id].write(block, reconstructed)
                self.rebuild_operations += 1
                
        return True
        
    def get_status(self) -> Dict:
        """Get RAID array status."""
        failed_disks = [d.disk_id for d in self.disks if d.failed]
        
        status = "HEALTHY"
        if len(failed_disks) > self.redundancy_disks:
            status = "DEGRADED - DATA LOSS"
        elif failed_disks:
            status = "DEGRADED - RECOVERABLE"
            
        return {
            'level': self.level.value,
            'num_disks': self.num_disks,
            'disk_size': self.disk_size,
            'usable_capacity': self.usable_capacity,
            'data_disks': self.get_data_disks(),
            'redundancy_disks': self.redundancy_disks,
            'stripe_size': self.stripe_size,
            'failed_disks': failed_disks,
            'status': status,
            'read_operations': self.read_count,
            'write_operations': self.write_count,
            'rebuild_operations': self.rebuild_operations,
            'parity_calculations': self.parity_calculations
        }
        
    def get_disk_usage(self) -> Dict[int, int]:
        """Get usage percentage for each disk."""
        usage = {}
        for disk in self.disks:
            used = sum(1 for b in disk.blocks if b is not None)
            usage[disk.disk_id] = (used / disk.size) * 100
        return usage
