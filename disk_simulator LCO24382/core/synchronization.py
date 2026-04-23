"""
Synchronization Primitives Module for OS Core Simulator.
Implements Semaphores, Mutexes, Monitors, and condition variables.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Callable, Any
from threading import Lock as ThreadLock
from collections import deque
import time
from collections import defaultdict


class SyncPrimitiveType(Enum):
    """Types of synchronization primitives."""
    SEMAPHORE = "semaphore"
    MUTEX = "mutex"
    RW_LOCK = "rw_lock"
    MONITOR = "monitor"
    BARRIER = "barrier"


class WaitState(Enum):
    """Process wait states for synchronization."""
    RUNNING = "running"
    WAITING = "waiting"
    BLOCKED = "blocked"
    TIMED_WAIT = "timed_wait"


@dataclass
class ProcessSyncState:
    """Synchronization state for a process."""
    process_id: int
    state: WaitState = WaitState.RUNNING
    waiting_on: Optional[str] = None  # Name of primitive waiting on
    wait_start_time: float = 0.0
    acquired_resources: List[str] = field(default_factory=list)


class Semaphore:
    """
    Counting semaphore implementation.
    Supports wait (P) and signal (V) operations.
    """
    
    def __init__(self, name: str, initial_value: int = 1):
        self.name = name
        self.value = initial_value
        self.max_value = initial_value
        self.waiting_queue: deque = deque()  # Process IDs waiting
        self.history: List[Dict] = []
        
    def wait(self, pid: int, timeout: Optional[float] = None) -> bool:
        """
        P operation - decrement semaphore, block if negative.
        Returns True if acquired, False if timeout.
        """
        self.value -= 1
        
        if self.value < 0:
            # Need to block
            self.waiting_queue.append(pid)
            self._log_operation("WAIT", pid, f"Blocked, queue: {list(self.waiting_queue)}")
            return False  # Process should block
        else:
            self._log_operation("ACQUIRE", pid, f"Value: {self.value}")
            return True
            
    def signal(self, pid: int) -> Optional[int]:
        """
        V operation - increment semaphore, wake waiting process.
        Returns PID of awakened process or None.
        """
        self.value += 1
        awakened = None
        
        if self.waiting_queue:
            awakened = self.waiting_queue.popleft()
            self._log_operation("SIGNAL", pid, f"Awakened: {awakened}, queue: {list(self.waiting_queue)}")
        else:
            self._log_operation("SIGNAL", pid, f"Value: {self.value}")
            
        return awakened
        
    def try_wait(self, pid: int) -> bool:
        """Non-blocking attempt to acquire semaphore."""
        if self.value > 0:
            self.value -= 1
            self._log_operation("TRY_ACQUIRE", pid, f"Success, value: {self.value}")
            return True
        else:
            self._log_operation("TRY_ACQUIRE", pid, "Failed")
            return False
            
    def get_value(self) -> int:
        """Get current semaphore value."""
        return self.value
        
    def get_stats(self) -> Dict:
        """Get semaphore statistics."""
        return {
            'name': self.name,
            'value': self.value,
            'max_value': self.max_value,
            'waiting_count': len(self.waiting_queue),
            'waiting_queue': list(self.waiting_queue),
            'history': self.history[-10:]  # Last 10 operations
        }
        
    def _log_operation(self, op: str, pid: int, details: str):
        """Log operation for analysis."""
        self.history.append({
            'time': time.time(),
            'operation': op,
            'pid': pid,
            'value': self.value,
            'details': details
        })


class Mutex:
    """
    Mutual exclusion lock.
    Binary semaphore with ownership tracking.
    """
    
    def __init__(self, name: str, recursive: bool = False):
        self.name = name
        self.locked = False
        self.owner: Optional[int] = None
        self.recursive = recursive
        self.lock_count = 0  # For recursive mutex
        self.waiting_queue: deque = deque()
        self.history: List[Dict] = []
        
    def acquire(self, pid: int, timeout: Optional[float] = None) -> bool:
        """Acquire mutex lock."""
        if self.locked:
            if self.recursive and self.owner == pid:
                self.lock_count += 1
                self._log_operation("RECURSIVE_LOCK", pid, f"Count: {self.lock_count}")
                return True
            else:
                # Block
                self.waiting_queue.append(pid)
                self._log_operation("BLOCK", pid, f"Owner: {self.owner}, queue: {list(self.waiting_queue)}")
                return False
        else:
            self.locked = True
            self.owner = pid
            self.lock_count = 1
            self._log_operation("LOCK", pid, "Acquired")
            return True
            
    def release(self, pid: int) -> Optional[int]:
        """Release mutex lock. Returns awakened process or None."""
        if self.owner != pid:
            self._log_operation("RELEASE_FAIL", pid, f"Not owner (owner={self.owner})")
            return None
            
        if self.recursive and self.lock_count > 1:
            self.lock_count -= 1
            self._log_operation("RECURSIVE_UNLOCK", pid, f"Count: {self.lock_count}")
            return None
            
        self.locked = False
        self.owner = None
        self.lock_count = 0
        
        awakened = None
        if self.waiting_queue:
            awakened = self.waiting_queue.popleft()
            self.owner = awakened
            self.locked = True
            self.lock_count = 1
            self._log_operation("UNLOCK", pid, f"Handoff to: {awakened}")
        else:
            self._log_operation("UNLOCK", pid, "Released")
            
        return awakened
        
    def try_acquire(self, pid: int) -> bool:
        """Non-blocking acquire attempt."""
        if not self.locked:
            self.locked = True
            self.owner = pid
            self.lock_count = 1
            self._log_operation("TRY_LOCK", pid, "Success")
            return True
        elif self.recursive and self.owner == pid:
            self.lock_count += 1
            self._log_operation("TRY_RECURSIVE", pid, f"Count: {self.lock_count}")
            return True
        else:
            self._log_operation("TRY_LOCK", pid, "Failed")
            return False
            
    def get_stats(self) -> Dict:
        """Get mutex statistics."""
        return {
            'name': self.name,
            'locked': self.locked,
            'owner': self.owner,
            'recursive': self.recursive,
            'lock_count': self.lock_count,
            'waiting_count': len(self.waiting_queue),
            'waiting_queue': list(self.waiting_queue),
            'history': self.history[-10:]
        }
        
    def _log_operation(self, op: str, pid: int, details: str):
        """Log operation."""
        self.history.append({
            'time': time.time(),
            'operation': op,
            'pid': pid,
            'locked': self.locked,
            'owner': self.owner,
            'details': details
        })


class RWLock:
    """
    Reader-Writer Lock.
    Multiple readers or single writer.
    """
    
    def __init__(self, name: str, prefer_writer: bool = True):
        self.name = name
        self.prefer_writer = prefer_writer
        self.active_readers = 0
        self.active_writer: Optional[int] = None
        self.waiting_readers: deque = deque()
        self.waiting_writers: deque = deque()
        self.history: List[Dict] = []
        
    def acquire_read(self, pid: int) -> bool:
        """Acquire read lock."""
        if self.active_writer is None and (not self.prefer_writer or len(self.waiting_writers) == 0):
            self.active_readers += 1
            self._log_operation("READ_LOCK", pid, f"Readers: {self.active_readers}")
            return True
        else:
            self.waiting_readers.append(pid)
            self._log_operation("READ_WAIT", pid, f"Queue: {list(self.waiting_readers)}")
            return False
            
    def release_read(self, pid: int) -> Optional[int]:
        """Release read lock. Returns awakened writer or None."""
        self.active_readers -= 1
        self._log_operation("READ_UNLOCK", pid, f"Readers: {self.active_readers}")
        
        # If no more readers and writers waiting, wake one
        if self.active_readers == 0 and self.waiting_writers:
            writer = self.waiting_writers.popleft()
            self.active_writer = writer
            self._log_operation("WAKE_WRITER", pid, f"Writer: {writer}")
            return writer
        return None
        
    def acquire_write(self, pid: int) -> bool:
        """Acquire write lock."""
        if self.active_readers == 0 and self.active_writer is None:
            self.active_writer = pid
            self._log_operation("WRITE_LOCK", pid, "Acquired")
            return True
        else:
            self.waiting_writers.append(pid)
            self._log_operation("WRITE_WAIT", pid, f"Queue: {list(self.waiting_writers)}")
            return False
            
    def release_write(self, pid: int) -> List[int]:
        """Release write lock. Returns list of awakened processes."""
        self.active_writer = None
        self._log_operation("WRITE_UNLOCK", pid, "Released")
        
        awakened = []
        
        # Prefer writers: wake waiting writer first
        if self.prefer_writer and self.waiting_writers:
            writer = self.waiting_writers.popleft()
            self.active_writer = writer
            awakened.append(writer)
            self._log_operation("WAKE_WRITER", pid, f"Writer: {writer}")
        # Otherwise wake all waiting readers
        elif self.waiting_readers:
            while self.waiting_readers:
                reader = self.waiting_readers.popleft()
                self.active_readers += 1
                awakened.append(reader)
            self._log_operation("WAKE_READERS", pid, f"Readers: {awakened}")
        # If no readers, check for writers
        elif self.waiting_writers:
            writer = self.waiting_writers.popleft()
            self.active_writer = writer
            awakened.append(writer)
            
        return awakened
        
    def get_stats(self) -> Dict:
        """Get RW lock statistics."""
        return {
            'name': self.name,
            'active_readers': self.active_readers,
            'active_writer': self.active_writer,
            'waiting_readers': list(self.waiting_readers),
            'waiting_writers': list(self.waiting_writers),
            'prefer_writer': self.prefer_writer,
            'history': self.history[-10:]
        }
        
    def _log_operation(self, op: str, pid: int, details: str):
        """Log operation."""
        self.history.append({
            'time': time.time(),
            'operation': op,
            'pid': pid,
            'readers': self.active_readers,
            'writer': self.active_writer,
            'details': details
        })


class Barrier:
    """
    Barrier synchronization primitive.
    Processes wait until all reach the barrier.
    """
    
    def __init__(self, name: str, count: int):
        self.name = name
        self.count = count  # Number of processes required
        self.waiting = 0
        self.waiting_queue: List[int] = []
        self.generation = 0  # For reuse
        self.history: List[Dict] = []
        
    def arrive(self, pid: int) -> Tuple[bool, List[int]]:
        """
        Arrive at barrier.
        Returns (released, awakened_processes)
        """
        self.waiting += 1
        self.waiting_queue.append(pid)
        
        if self.waiting >= self.count:
            # All arrived, release everyone
            awakened = self.waiting_queue.copy()
            self._log_operation("BARRIER_RELEASE", pid, f"All {self.count} arrived")
            self.waiting = 0
            self.waiting_queue = []
            self.generation += 1
            return True, awakened
        else:
            self._log_operation("BARRIER_WAIT", pid, f"Waiting {self.waiting}/{self.count}")
            return False, []
            
    def get_stats(self) -> Dict:
        """Get barrier statistics."""
        return {
            'name': self.name,
            'required': self.count,
            'waiting': self.waiting,
            'generation': self.generation,
            'waiting_queue': self.waiting_queue.copy(),
            'history': self.history[-10:]
        }
        
    def _log_operation(self, op: str, pid: int, details: str):
        """Log operation."""
        self.history.append({
            'time': time.time(),
            'operation': op,
            'pid': pid,
            'generation': self.generation,
            'details': details
        })


class SynchronizationManager:
    """
    Central manager for all synchronization primitives.
    Tracks process synchronization states and potential deadlocks.
    """
    
    def __init__(self):
        self.semaphores: Dict[str, Semaphore] = {}
        self.mutexes: Dict[str, Mutex] = {}
        self.rw_locks: Dict[str, RWLock] = {}
        self.barriers: Dict[str, Barrier] = {}
        self.process_states: Dict[int, ProcessSyncState] = {}
        self.wait_graph: Dict[int, Set[int]] = defaultdict(set)
        
    def create_semaphore(self, name: str, initial: int = 1) -> Semaphore:
        """Create a new semaphore."""
        sem = Semaphore(name, initial)
        self.semaphores[name] = sem
        return sem
        
    def create_mutex(self, name: str, recursive: bool = False) -> Mutex:
        """Create a new mutex."""
        mutex = Mutex(name, recursive)
        self.mutexes[name] = mutex
        return mutex
        
    def create_rw_lock(self, name: str, prefer_writer: bool = True) -> RWLock:
        """Create a new RW lock."""
        lock = RWLock(name, prefer_writer)
        self.rw_locks[name] = lock
        return lock
        
    def create_barrier(self, name: str, count: int) -> Barrier:
        """Create a new barrier."""
        barrier = Barrier(name, count)
        self.barriers[name] = barrier
        return barrier
        
    def register_process(self, pid: int):
        """Register a process for synchronization tracking."""
        self.process_states[pid] = ProcessSyncState(process_id=pid)
        
    def semaphore_wait(self, name: str, pid: int) -> bool:
        """Execute semaphore wait operation."""
        if name not in self.semaphores:
            return False
            
        sem = self.semaphores[name]
        acquired = sem.wait(pid)
        
        if not acquired:
            self.process_states[pid].state = WaitState.BLOCKED
            self.process_states[pid].waiting_on = name
            # Add wait edge for deadlock detection
            for waiting_pid in sem.waiting_queue:
                if waiting_pid != pid:
                    self.wait_graph[pid].add(waiting_pid)
        else:
            self.process_states[pid].acquired_resources.append(name)
            
        return acquired
        
    def semaphore_signal(self, name: str, pid: int) -> Optional[int]:
        """Execute semaphore signal operation."""
        if name not in self.semaphores:
            return None
            
        sem = self.semaphores[name]
        awakened = sem.signal(pid)
        
        if awakened is not None:
            self.process_states[awakened].state = WaitState.RUNNING
            self.process_states[awakened].waiting_on = None
            self.process_states[awakened].acquired_resources.append(name)
            # Remove wait edges
            if awakened in self.wait_graph:
                del self.wait_graph[awakened]
                
        if name in self.process_states[pid].acquired_resources:
            self.process_states[pid].acquired_resources.remove(name)
            
        return awakened
        
    def detect_sync_deadlock(self) -> Tuple[bool, List[int]]:
        """Detect deadlock in synchronization wait graph."""
        visited = set()
        rec_stack = set()
        deadlocked = set()
        
        def dfs(node: int, path: List[int]) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self.wait_graph.get(node, set()):
                if neighbor not in visited:
                    if dfs(neighbor, path + [neighbor]):
                        return True
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    deadlocked.update(cycle)
                    return True
                    
            rec_stack.remove(node)
            return False
            
        for pid in self.process_states:
            if pid not in visited:
                dfs(pid, [pid])
                
        return len(deadlocked) > 0, list(deadlocked)
        
    def get_all_stats(self) -> Dict:
        """Get statistics for all primitives."""
        return {
            'semaphores': {name: sem.get_stats() for name, sem in self.semaphores.items()},
            'mutexes': {name: mutex.get_stats() for name, mutex in self.mutexes.items()},
            'rw_locks': {name: lock.get_stats() for name, lock in self.rw_locks.items()},
            'barriers': {name: bar.get_stats() for name, bar in self.barriers.items()},
            'process_states': {
                pid: {
                    'state': p.state.value,
                    'waiting_on': p.waiting_on,
                    'acquired': p.acquired_resources
                }
                for pid, p in self.process_states.items()
            },
            'wait_graph': {pid: list(waiting) for pid, waiting in self.wait_graph.items()}
        }
