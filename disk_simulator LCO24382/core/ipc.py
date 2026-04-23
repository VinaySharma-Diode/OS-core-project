"""
Inter-Process Communication (IPC) Module for OS Core Simulator.
Implements Shared Memory, Message Queues, Pipes, and Signals.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable, Set
from collections import deque
import time
from collections import defaultdict


class IPCType(Enum):
    """Types of IPC mechanisms."""
    SHARED_MEMORY = "shared_memory"
    MESSAGE_QUEUE = "message_queue"
    PIPE = "pipe"
    SIGNAL = "signal"
    SOCKET = "socket"


class MessageType(Enum):
    """Types of IPC messages."""
    DATA = "data"
    CONTROL = "control"
    SIGNAL = "signal"
    SYNC = "synchronization"


@dataclass
class IPCMessage:
    """Represents an IPC message."""
    sender: int
    type: MessageType
    data: Any
    timestamp: float = field(default_factory=time.time)
    priority: int = 0  # Higher = more urgent
    

class SharedMemorySegment:
    """
    Shared memory segment with read/write access control.
    Multiple processes can attach and access.
    """
    
    def __init__(self, name: str, size: int, creator_pid: int):
        self.name = name
        self.size = size
        self.creator = creator_pid
        self.data: bytearray = bytearray(size)
        self.attached_processes: Set[int] = {creator_pid}
        self.read_locks: Set[int] = set()
        self.write_lock: Optional[int] = None
        self.access_log: List[Dict] = []
        self.read_count = 0
        self.write_count = 0
        
    def attach(self, pid: int, read_only: bool = False) -> bool:
        """Attach process to shared memory segment."""
        if pid in self.attached_processes:
            return True
        self.attached_processes.add(pid)
        self._log_access("ATTACH", pid, f"Read-only: {read_only}")
        return True
        
    def detach(self, pid: int) -> bool:
        """Detach process from shared memory segment."""
        if pid not in self.attached_processes:
            return False
        self.attached_processes.remove(pid)
        
        # Release any locks held
        if pid in self.read_locks:
            self.read_locks.remove(pid)
        if self.write_lock == pid:
            self.write_lock = None
            
        self._log_access("DETACH", pid, "")
        return True
        
    def read(self, pid: int, offset: int, length: int) -> Optional[bytes]:
        """Read from shared memory."""
        if pid not in self.attached_processes:
            return None
        if offset + length > self.size:
            return None
            
        self.read_count += 1
        self._log_access("READ", pid, f"Offset: {offset}, Length: {length}")
        return bytes(self.data[offset:offset + length])
        
    def write(self, pid: int, offset: int, data: bytes) -> bool:
        """Write to shared memory."""
        if pid not in self.attached_processes:
            return False
        if self.write_lock is not None and self.write_lock != pid:
            return False
        if offset + len(data) > self.size:
            return False
            
        self.write_count += 1
        self.data[offset:offset + len(data)] = data
        self._log_access("WRITE", pid, f"Offset: {offset}, Length: {len(data)}")
        return True
        
    def acquire_read_lock(self, pid: int) -> bool:
        """Acquire read lock (multiple readers allowed)."""
        if pid not in self.attached_processes:
            return False
        if self.write_lock is not None:
            return False  # Writer active
        self.read_locks.add(pid)
        return True
        
    def release_read_lock(self, pid: int):
        """Release read lock."""
        self.read_locks.discard(pid)
        
    def acquire_write_lock(self, pid: int) -> bool:
        """Acquire write lock (exclusive)."""
        if pid not in self.attached_processes:
            return False
        if len(self.read_locks) > 0:
            return False  # Readers active
        if self.write_lock is not None:
            return False  # Another writer
        self.write_lock = pid
        return True
        
    def release_write_lock(self, pid: int):
        """Release write lock."""
        if self.write_lock == pid:
            self.write_lock = None
            
    def _log_access(self, op: str, pid: int, details: str):
        """Log memory access."""
        self.access_log.append({
            'time': time.time(),
            'operation': op,
            'pid': pid,
            'details': details
        })
        
    def get_stats(self) -> Dict:
        """Get segment statistics."""
        return {
            'name': self.name,
            'size': self.size,
            'creator': self.creator,
            'attached_processes': list(self.attached_processes),
            'read_count': self.read_count,
            'write_count': self.write_count,
            'active_readers': len(self.read_locks),
            'active_writer': self.write_lock,
            'recent_access': self.access_log[-5:]
        }


class MessageQueue:
    """
    Message queue for process communication.
    Supports priority messages and blocking/non-blocking operations.
    """
    
    def __init__(self, name: str, max_messages: int = 100, max_size: int = 8192):
        self.name = name
        self.max_messages = max_messages
        self.max_size = max_size
        self.messages: deque = deque()
        self.receivers: Set[int] = set()
        self.permissions: Dict[int, str] = {}  # 'r', 'w', 'rw'
        self.blocked_senders: deque = deque()  # PIDs waiting to send
        self.blocked_receivers: deque = deque()  # PIDs waiting to receive
        self.message_count = 0
        self.total_bytes = 0
        
    def register(self, pid: int, mode: str = 'rw') -> bool:
        """Register process for queue access."""
        self.receivers.add(pid)
        self.permissions[pid] = mode
        return True
        
    def unregister(self, pid: int):
        """Unregister process from queue."""
        self.receivers.discard(pid)
        if pid in self.permissions:
            del self.permissions[pid]
            
    def send(self, pid: int, data: Any, msg_type: MessageType = MessageType.DATA,
             priority: int = 0, blocking: bool = True) -> bool:
        """Send message to queue."""
        if 'w' not in self.permissions.get(pid, ''):
            return False
            
        # Check if queue is full
        if len(self.messages) >= self.max_messages:
            if not blocking:
                return False
            self.blocked_senders.append(pid)
            return False  # Would block
            
        msg = IPCMessage(
            sender=pid,
            type=msg_type,
            data=data,
            priority=priority
        )
        
        # Insert by priority
        inserted = False
        for i, existing in enumerate(self.messages):
            if priority > existing.priority:
                self.messages.insert(i, msg)
                inserted = True
                break
        if not inserted:
            self.messages.append(msg)
            
        self.message_count += 1
        self.total_bytes += len(str(data).encode())
        
        # Wake blocked receivers
        if self.blocked_receivers:
            return True  # Signal that receivers should be woken
        return True
        
    def receive(self, pid: int, msg_type: Optional[MessageType] = None,
                blocking: bool = True) -> Optional[IPCMessage]:
        """Receive message from queue."""
        if 'r' not in self.permissions.get(pid, ''):
            return None
            
        # Find matching message
        for i, msg in enumerate(self.messages):
            if msg_type is None or msg.type == msg_type:
                # Remove from queue
                self.messages.remove(msg)
                return msg
                
        if blocking:
            self.blocked_receivers.append(pid)
            return None  # Would block
        return None
        
    def peek(self, pid: int) -> Optional[IPCMessage]:
        """Peek at next message without removing."""
        if 'r' not in self.permissions.get(pid, ''):
            return None
        return self.messages[0] if self.messages else None
        
    def get_stats(self) -> Dict:
        """Get queue statistics."""
        return {
            'name': self.name,
            'messages': len(self.messages),
            'max_messages': self.max_messages,
            'registered_processes': list(self.receivers),
            'message_count': self.message_count,
            'total_bytes': self.total_bytes,
            'blocked_senders': list(self.blocked_senders),
            'blocked_receivers': list(self.blocked_receivers),
            'oldest_message_age': time.time() - self.messages[0].timestamp if self.messages else 0
        }


class Pipe:
    """
    Unidirectional pipe for IPC.
    Classic producer-consumer pattern.
    """
    
    def __init__(self, name: str, buffer_size: int = 4096):
        self.name = name
        self.buffer_size = buffer_size
        self.buffer: deque = deque()
        self.writer: Optional[int] = None
        self.readers: Set[int] = set()
        self.closed_write = False
        self.closed_read = False
        self.bytes_written = 0
        self.bytes_read = 0
        
    def open_write(self, pid: int) -> bool:
        """Open pipe for writing (only one writer allowed)."""
        if self.writer is not None:
            return False
        self.writer = pid
        return True
        
    def open_read(self, pid: int) -> bool:
        """Open pipe for reading (multiple readers allowed)."""
        self.readers.add(pid)
        return True
        
    def write(self, pid: int, data: bytes) -> int:
        """Write data to pipe. Returns bytes written or -1 if error."""
        if self.writer != pid or self.closed_write:
            return -1
            
        available = self.buffer_size - sum(len(d) for d in self.buffer)
        to_write = min(len(data), available)
        
        if to_write > 0:
            self.buffer.append(data[:to_write])
            self.bytes_written += to_write
            
        return to_write
        
    def read(self, pid: int, max_bytes: int) -> Optional[bytes]:
        """Read data from pipe. Returns data or None if closed."""
        if pid not in self.readers or self.closed_read:
            return None
            
        if not self.buffer and self.closed_write:
            return b''  # EOF
            
        result = bytearray()
        while self.buffer and len(result) < max_bytes:
            chunk = self.buffer[0]
            needed = max_bytes - len(result)
            
            if len(chunk) <= needed:
                result.extend(chunk)
                self.buffer.popleft()
            else:
                result.extend(chunk[:needed])
                self.buffer[0] = chunk[needed:]
                
        self.bytes_read += len(result)
        return bytes(result)
        
    def close_write(self):
        """Close write end of pipe."""
        self.closed_write = True
        self.writer = None
        
    def close_read(self, pid: int):
        """Close read end for specific process."""
        self.readers.discard(pid)
        if not self.readers:
            self.closed_read = True
            
    def get_stats(self) -> Dict:
        """Get pipe statistics."""
        return {
            'name': self.name,
            'buffer_used': sum(len(d) for d in self.buffer),
            'buffer_size': self.buffer_size,
            'writer': self.writer,
            'readers': list(self.readers),
            'bytes_written': self.bytes_written,
            'bytes_read': self.bytes_read,
            'write_closed': self.closed_write,
            'read_closed': self.closed_read
        }


class SignalHandler:
    """
    Signal handling system for IPC.
    Asynchronous notification mechanism.
    """
    
    def __init__(self):
        self.handlers: Dict[int, Dict[int, Callable]] = {}  # pid -> {signal -> handler}
        self.pending_signals: Dict[int, List[Dict]] = defaultdict(list)  # pid -> signals
        self.signal_count = 0
        
        # Standard signals
        self.SIGTERM = 15
        self.SIGINT = 2
        self.SIGKILL = 9
        self.SIGUSR1 = 10
        self.SIGUSR2 = 12
        self.SIGALRM = 14
        self.SIGCHLD = 17
        
    def register_handler(self, pid: int, signal: int, handler: Callable):
        """Register signal handler for process."""
        if pid not in self.handlers:
            self.handlers[pid] = {}
        self.handlers[pid][signal] = handler
        
    def send_signal(self, sender: int, target: int, signal: int, data: Any = None):
        """Send signal to process."""
        self.signal_count += 1
        
        sig_info = {
            'signal': signal,
            'sender': sender,
            'timestamp': time.time(),
            'data': data
        }
        
        # SIGKILL and SIGSTOP cannot be caught
        if signal == self.SIGKILL:
            return {'action': 'terminate', 'signal': sig_info}
            
        # Add to pending
        self.pending_signals[target].append(sig_info)
        
        # Check if handler exists
        if target in self.handlers and signal in self.handlers[target]:
            try:
                result = self.handlers[target][signal](sig_info)
                return {'handled': True, 'result': result, 'signal': sig_info}
            except Exception as e:
                return {'handled': False, 'error': str(e), 'signal': sig_info}
        else:
            # Default action
            if signal == self.SIGTERM or signal == self.SIGINT:
                return {'action': 'terminate', 'signal': sig_info}
            return {'handled': False, 'default': True, 'signal': sig_info}
            
    def get_pending_signals(self, pid: int) -> List[Dict]:
        """Get and clear pending signals for process."""
        signals = self.pending_signals[pid].copy()
        self.pending_signals[pid] = []
        return signals
        
    def get_stats(self) -> Dict:
        """Get signal statistics."""
        return {
            'registered_handlers': sum(len(h) for h in self.handlers.values()),
            'pending_signals': {pid: len(sigs) for pid, sigs in self.pending_signals.items()},
            'total_sent': self.signal_count
        }


class IPCManager:
    """
    Central manager for all IPC mechanisms.
    """
    
    def __init__(self):
        self.shared_memory: Dict[str, SharedMemorySegment] = {}
        self.message_queues: Dict[str, MessageQueue] = {}
        self.pipes: Dict[str, Pipe] = {}
        self.signals = SignalHandler()
        
    def create_shared_memory(self, name: str, size: int, creator_pid: int) -> SharedMemorySegment:
        """Create shared memory segment."""
        segment = SharedMemorySegment(name, size, creator_pid)
        self.shared_memory[name] = segment
        return segment
        
    def remove_shared_memory(self, name: str, pid: int) -> bool:
        """Remove shared memory segment (only creator can remove)."""
        if name not in self.shared_memory:
            return False
        if self.shared_memory[name].creator != pid:
            return False
        del self.shared_memory[name]
        return True
        
    def create_message_queue(self, name: str, max_messages: int = 100) -> MessageQueue:
        """Create message queue."""
        queue = MessageQueue(name, max_messages)
        self.message_queues[name] = queue
        return queue
        
    def remove_message_queue(self, name: str):
        """Remove message queue."""
        if name in self.message_queues:
            del self.message_queues[name]
            
    def create_pipe(self, name: str, buffer_size: int = 4096) -> Pipe:
        """Create pipe."""
        pipe = Pipe(name, buffer_size)
        self.pipes[name] = pipe
        return pipe
        
    def remove_pipe(self, name: str):
        """Remove pipe."""
        if name in self.pipes:
            del self.pipes[name]
            
    def get_stats(self) -> Dict:
        """Get comprehensive IPC statistics."""
        return {
            'shared_memory': {
                name: seg.get_stats() for name, seg in self.shared_memory.items()
            },
            'message_queues': {
                name: q.get_stats() for name, q in self.message_queues.items()
            },
            'pipes': {
                name: p.get_stats() for name, p in self.pipes.items()
            },
            'signals': self.signals.get_stats()
        }
        
    def get_process_ipc_info(self, pid: int) -> Dict:
        """Get IPC information for a specific process."""
        return {
            'shared_memory_attached': [
                name for name, seg in self.shared_memory.items()
                if pid in seg.attached_processes
            ],
            'message_queues_registered': [
                name for name, q in self.message_queues.items()
                if pid in q.receivers
            ],
            'pipes': {
                'writing': [name for name, p in self.pipes.items() if p.writer == pid],
                'reading': [name for name, p in self.pipes.items() if pid in p.readers]
            },
            'pending_signals': self.signals.get_pending_signals(pid)
        }
