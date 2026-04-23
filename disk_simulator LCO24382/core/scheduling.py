"""
Disk Scheduling Algorithms for OS Core.
Implements: FCFS, SSTF, SCAN, C-SCAN, LOOK, C-LOOK
"""

from enum import Enum
from typing import List, Tuple, Optional
from dataclasses import dataclass
import time


class SchedulingAlgorithm(Enum):
    """Disk scheduling algorithms."""
    FCFS = "fcfs"           # First Come First Serve
    SSTF = "sstf"           # Shortest Seek Time First
    SCAN = "scan"           # Elevator algorithm
    C_SCAN = "c_scan"       # Circular SCAN
    LOOK = "look"           # LOOK (SCAN without going to end)
    C_LOOK = "c_look"       # Circular LOOK


@dataclass
class DiskRequest:
    """Represents a disk I/O request."""
    track: int
    arrival_time: float
    request_type: str = "read"  # read, write
    process_id: int = 0
    
    def __repr__(self):
        return f"DiskRequest(track={self.track}, type={self.request_type}, pid={self.process_id})"


class DiskScheduler:
    """
    Disk scheduling controller.
    Manages the request queue and executes scheduling algorithms.
    """
    
    def __init__(self, total_tracks: int = 200, initial_head: int = 0):
        self.total_tracks = total_tracks
        self.head_position = initial_head
        self.request_queue: List[DiskRequest] = []
        self.direction = 1  # 1 = moving up, -1 = moving down
        self.algorithm = SchedulingAlgorithm.FCFS
        self.completed_requests: List[DiskRequest] = []
        self.total_seek_time = 0
        self.total_wait_time = 0
        
    def add_request(self, track: int, request_type: str = "read", process_id: int = 0):
        """Add a new disk request to the queue."""
        request = DiskRequest(
            track=track,
            arrival_time=time.time(),
            request_type=request_type,
            process_id=process_id
        )
        self.request_queue.append(request)
        return request
    
    def set_algorithm(self, algorithm: SchedulingAlgorithm):
        """Set the scheduling algorithm."""
        self.algorithm = algorithm
    
    def schedule(self) -> List[Tuple[int, int, float]]:
        """
        Execute scheduling algorithm and return the sequence.
        Returns list of (track, seek_distance, wait_time).
        """
        if not self.request_queue:
            return []
        
        if self.algorithm == SchedulingAlgorithm.FCFS:
            return self._fcfs()
        elif self.algorithm == SchedulingAlgorithm.SSTF:
            return self._sstf()
        elif self.algorithm == SchedulingAlgorithm.SCAN:
            return self._scan()
        elif self.algorithm == SchedulingAlgorithm.C_SCAN:
            return self._c_scan()
        elif self.algorithm == SchedulingAlgorithm.LOOK:
            return self._look()
        elif self.algorithm == SchedulingAlgorithm.C_LOOK:
            return self._c_look()
        else:
            return self._fcfs()
    
    def _fcfs(self) -> List[Tuple[int, int, float]]:
        """First Come First Serve scheduling."""
        result = []
        current_pos = self.head_position
        current_time = time.time()
        
        for request in self.request_queue:
            seek_distance = abs(request.track - current_pos)
            wait_time = current_time - request.arrival_time
            
            result.append((request.track, seek_distance, wait_time))
            self.total_seek_time += seek_distance
            self.total_wait_time += wait_time
            self.completed_requests.append(request)
            
            current_pos = request.track
            current_time += seek_distance * 0.001  # Simulate time
        
        self.head_position = current_pos
        self.request_queue = []
        return result
    
    def _sstf(self) -> List[Tuple[int, int, float]]:
        """Shortest Seek Time First scheduling."""
        result = []
        current_pos = self.head_position
        current_time = time.time()
        pending = self.request_queue.copy()
        
        while pending:
            # Find request with minimum seek time
            nearest = min(pending, key=lambda r: abs(r.track - current_pos))
            pending.remove(nearest)
            
            seek_distance = abs(nearest.track - current_pos)
            wait_time = current_time - nearest.arrival_time
            
            result.append((nearest.track, seek_distance, wait_time))
            self.total_seek_time += seek_distance
            self.total_wait_time += wait_time
            self.completed_requests.append(nearest)
            
            current_pos = nearest.track
            current_time += seek_distance * 0.001
        
        self.head_position = current_pos
        self.request_queue = []
        return result
    
    def _scan(self) -> List[Tuple[int, int, float]]:
        """SCAN (Elevator) scheduling - services requests while moving in one direction."""
        result = []
        current_pos = self.head_position
        current_time = time.time()
        
        # Sort requests
        requests_sorted = sorted(self.request_queue, key=lambda r: r.track)
        
        # Split into left and right of current position
        left = [r for r in requests_sorted if r.track < current_pos]
        right = [r for r in requests_sorted if r.track >= current_pos]
        
        # Service based on current direction, then reverse
        if self.direction == 1:  # Moving up
            service_order = right + list(reversed(left))
        else:  # Moving down
            service_order = list(reversed(left)) + right
        
        # Add end of disk if needed
        if self.direction == 1 and right:
            if right[-1].track < self.total_tracks - 1:
                # Go to end
                pass
        
        for request in service_order:
            seek_distance = abs(request.track - current_pos)
            wait_time = current_time - request.arrival_time
            
            result.append((request.track, seek_distance, wait_time))
            self.total_seek_time += seek_distance
            self.total_wait_time += wait_time
            self.completed_requests.append(request)
            
            current_pos = request.track
            current_time += seek_distance * 0.001
        
        self.head_position = current_pos
        self.direction *= -1  # Reverse direction
        self.request_queue = []
        return result
    
    def _c_scan(self) -> List[Tuple[int, int, float]]:
        """Circular SCAN - goes to end, jumps to start, continues in same direction."""
        result = []
        current_pos = self.head_position
        current_time = time.time()
        
        requests_sorted = sorted(self.request_queue, key=lambda r: r.track)
        
        # Service right side first (increasing track numbers)
        right = [r for r in requests_sorted if r.track >= current_pos]
        left = [r for r in requests_sorted if r.track < current_pos]
        
        service_order = right + left  # Complete the circle
        
        for request in service_order:
            seek_distance = abs(request.track - current_pos)
            wait_time = current_time - request.arrival_time
            
            result.append((request.track, seek_distance, wait_time))
            self.total_seek_time += seek_distance
            self.total_wait_time += wait_time
            self.completed_requests.append(request)
            
            current_pos = request.track
            current_time += seek_distance * 0.001
        
        self.head_position = current_pos
        self.request_queue = []
        return result
    
    def _look(self) -> List[Tuple[int, int, float]]:
        """LOOK - like SCAN but doesn't go to the end of disk."""
        result = []
        current_pos = self.head_position
        current_time = time.time()
        
        if not self.request_queue:
            return result
        
        requests_sorted = sorted(self.request_queue, key=lambda r: r.track)
        
        left = [r for r in requests_sorted if r.track < current_pos]
        right = [r for r in requests_sorted if r.track >= current_pos]
        
        if self.direction == 1:  # Moving up
            service_order = right + list(reversed(left))
        else:  # Moving down
            service_order = list(reversed(left)) + right
        
        for request in service_order:
            seek_distance = abs(request.track - current_pos)
            wait_time = current_time - request.arrival_time
            
            result.append((request.track, seek_distance, wait_time))
            self.total_seek_time += seek_distance
            self.total_wait_time += wait_time
            self.completed_requests.append(request)
            
            current_pos = request.track
            current_time += seek_distance * 0.001
        
        self.head_position = current_pos
        self.direction *= -1
        self.request_queue = []
        return result
    
    def _c_look(self) -> List[Tuple[int, int, float]]:
        """Circular LOOK - like C-SCAN but doesn't go to the end."""
        result = []
        current_pos = self.head_position
        current_time = time.time()
        
        if not self.request_queue:
            return result
        
        requests_sorted = sorted(self.request_queue, key=lambda r: r.track)
        
        right = [r for r in requests_sorted if r.track >= current_pos]
        left = [r for r in requests_sorted if r.track < current_pos]
        
        service_order = right + left  # Jump from highest to lowest
        
        for request in service_order:
            seek_distance = abs(request.track - current_pos)
            wait_time = current_time - request.arrival_time
            
            result.append((request.track, seek_distance, wait_time))
            self.total_seek_time += seek_distance
            self.total_wait_time += wait_time
            self.completed_requests.append(request)
            
            current_pos = request.track
            current_time += seek_distance * 0.001
        
        self.head_position = current_pos
        self.request_queue = []
        return result
    
    def get_statistics(self) -> dict:
        """Get scheduling statistics."""
        if not self.completed_requests:
            return {
                "algorithm": self.algorithm.value,
                "total_requests": 0,
                "total_seek_time": 0,
                "avg_seek_time": 0,
                "total_wait_time": 0,
                "avg_wait_time": 0,
                "throughput": 0
            }
        
        n = len(self.completed_requests)
        return {
            "algorithm": self.algorithm.value,
            "total_requests": n,
            "total_seek_time": self.total_seek_time,
            "avg_seek_time": self.total_seek_time / n,
            "total_wait_time": self.total_wait_time,
            "avg_wait_time": self.total_wait_time / n,
            "throughput": n / max(1, self.total_seek_time) * 1000
        }
    
    def reset(self):
        """Reset the scheduler state."""
        self.head_position = 0
        self.request_queue = []
        self.completed_requests = []
        self.total_seek_time = 0
        self.total_wait_time = 0
        self.direction = 1


def compare_algorithms(requests: List[int], total_tracks: int = 200) -> dict:
    """
    Compare all scheduling algorithms with the same request set.
    Returns statistics for each algorithm.
    """
    results = {}
    
    for algo in SchedulingAlgorithm:
        scheduler = DiskScheduler(total_tracks)
        scheduler.set_algorithm(algo)
        
        for track in requests:
            scheduler.add_request(track)
        
        scheduler.schedule()
        results[algo.value] = scheduler.get_statistics()
    
    return results


# Example usage and testing
if __name__ == "__main__":
    # Test with sample request queue
    test_requests = [98, 183, 37, 122, 14, 124, 65, 67]
    
    print("Disk Scheduling Algorithm Comparison")
    print("=" * 50)
    print(f"Initial head position: 53")
    print(f"Request queue: {test_requests}")
    print()
    
    results = compare_algorithms(test_requests, 200)
    
    for algo_name, stats in results.items():
        print(f"\n{algo_name.upper()}:")
        print(f"  Total seek time: {stats['total_seek_time']}")
        print(f"  Average seek time: {stats['avg_seek_time']:.2f}")
        print(f"  Throughput: {stats['throughput']:.2f} requests/unit time")
