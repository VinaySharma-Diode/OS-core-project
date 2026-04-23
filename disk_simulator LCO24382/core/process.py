"""
Process Management Module for OS Core.
Implements: Process lifecycle, CPU scheduling, I/O operations, IPC
"""

from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import deque
import time
import random


class ProcessState(Enum):
    """Process states in the lifecycle."""
    NEW = auto()
    READY = auto()
    RUNNING = auto()
    WAITING = auto()  # Blocked for I/O
    TERMINATED = auto()


class ProcessType(Enum):
    """Types of processes."""
    CPU_BOUND = "cpu_bound"
    IO_BOUND = "io_bound"
    INTERACTIVE = "interactive"


@dataclass
class IORequest:
    """Represents an I/O operation request."""
    device_type: str  # disk, network, etc.
    operation: str    # read, write
    duration: float   # Expected duration in ms
    start_time: float = field(default_factory=time.time)
    completed: bool = False


@dataclass
class Process:
    """Represents an OS process."""
    pid: int
    name: str
    priority: int = 5
    arrival_time: float = field(default_factory=time.time)
    burst_time: float = 100.0  # Total CPU time needed (ms)
    io_requests: List[IORequest] = field(default_factory=list)
    state: ProcessState = ProcessState.NEW
    process_type: ProcessType = ProcessType.CPU_BOUND
    
    # Execution tracking
    cpu_time_used: float = 0.0
    io_time_used: float = 0.0
    wait_time: float = 0.0
    turnaround_time: float = 0.0
    completion_time: Optional[float] = None
    
    # Memory requirements
    memory_required: int = 10  # Pages
    working_set: List[int] = field(default_factory=list)
    
    # Scheduling
    remaining_time: float = field(init=False)
    last_cpu_start: Optional[float] = None
    
    def __post_init__(self):
        self.remaining_time = self.burst_time
        if not self.working_set:
            self.working_set = random.sample(range(100), min(self.memory_required, 100))


class CPUSchedulingAlgorithm(Enum):
    """CPU scheduling algorithms."""
    FCFS = "fcfs"
    SJF = "sjf"           # Shortest Job First
    SRTF = "srtf"         # Shortest Remaining Time First
    ROUND_ROBIN = "rr"
    PRIORITY = "priority"
    MULTILEVEL_FEEDBACK = "mlfq"


@dataclass
class CPU:
    """Simulates CPU execution."""
    speed_mhz: float = 1000.0
    current_process: Optional[Process] = None
    idle_time: float = 0.0
    busy_time: float = 0.0
    context_switches: int = 0


class ProcessScheduler:
    """
    Process scheduler managing ready queue and CPU allocation.
    """
    
    def __init__(self, num_cpus: int = 1, time_quantum: float = 10.0):
        self.num_cpus = num_cpus
        self.cpus: List[CPU] = [CPU() for _ in range(num_cpus)]
        self.time_quantum = time_quantum
        self.algorithm = CPUSchedulingAlgorithm.FCFS
        
        # Process queues
        self.ready_queue: deque = deque()
        self.waiting_queue: List[Process] = []
        self.all_processes: Dict[int, Process] = {}
        self.terminated_processes: List[Process] = []
        
        # Statistics
        self.total_processes = 0
        self.total_context_switches = 0
        
        # MLFQ queues (for Multilevel Feedback Queue)
        self.mlfq_queues: List[deque] = [deque() for _ in range(3)]
        self.mlfq_quantums = [self.time_quantum, self.time_quantum * 2, self.time_quantum * 4]
    
    def create_process(self, name: str, burst_time: float, 
                       priority: int = 5,
                       process_type: ProcessType = ProcessType.CPU_BOUND,
                       io_ops: int = 0) -> Process:
        """Create a new process."""
        pid = self.total_processes + 1
        
        # Generate I/O requests for I/O bound processes
        io_requests = []
        if io_ops > 0:
            for _ in range(io_ops):
                io_requests.append(IORequest(
                    device_type="disk",
                    operation=random.choice(["read", "write"]),
                    duration=random.uniform(5, 20)
                ))
        
        process = Process(
            pid=pid,
            name=name,
            priority=priority,
            burst_time=burst_time,
            io_requests=io_requests,
            process_type=process_type
        )
        
        process.state = ProcessState.READY
        self.all_processes[pid] = process
        self.total_processes += 1
        
        # Add to appropriate queue
        if self.algorithm == CPUSchedulingAlgorithm.MULTILEVEL_FEEDBACK:
            self.mlfq_queues[0].append(process)
        else:
            self.ready_queue.append(process)
        
        return process
    
    def set_algorithm(self, algorithm: CPUSchedulingAlgorithm):
        """Set the CPU scheduling algorithm."""
        self.algorithm = algorithm
    
    def schedule(self, current_time: float) -> List[Tuple[int, Optional[Process], float]]:
        """
        Execute one scheduling step.
        Returns list of (cpu_id, assigned_process, time_slice).
        """
        results = []
        
        for cpu_id, cpu in enumerate(self.cpus):
            if cpu.current_process is None or self._should_preempt(cpu.current_process, current_time):
                # Context switch
                if cpu.current_process:
                    self._handle_process_preemption(cpu.current_process, current_time)
                
                # Get next process
                next_process = self._get_next_process()
                
                if next_process:
                    cpu.current_process = next_process
                    next_process.state = ProcessState.RUNNING
                    next_process.last_cpu_start = current_time
                    cpu.context_switches += 1
                    
                    # Calculate time slice
                    time_slice = self._calculate_time_slice(next_process)
                    results.append((cpu_id, next_process, time_slice))
                else:
                    cpu.idle_time += 1
                    results.append((cpu_id, None, 0))
            else:
                # Continue current process
                process = cpu.current_process
                time_slice = min(self.time_quantum, process.remaining_time)
                results.append((cpu_id, process, time_slice))
        
        return results
    
    def _get_next_process(self) -> Optional[Process]:
        """Get next process based on scheduling algorithm."""
        if self.algorithm == CPUSchedulingAlgorithm.MULTILEVEL_FEEDBACK:
            for queue in self.mlfq_queues:
                if queue:
                    return queue.popleft()
            return None
        
        elif self.algorithm == CPUSchedulingAlgorithm.SJF:
            if not self.ready_queue:
                return None
            shortest = min(self.ready_queue, key=lambda p: p.remaining_time)
            self.ready_queue.remove(shortest)
            return shortest
        
        elif self.algorithm == CPUSchedulingAlgorithm.SRTF:
            if not self.ready_queue:
                return None
            shortest = min(self.ready_queue, key=lambda p: p.remaining_time)
            self.ready_queue.remove(shortest)
            return shortest
        
        elif self.algorithm == CPUSchedulingAlgorithm.PRIORITY:
            if not self.ready_queue:
                return None
            highest = min(self.ready_queue, key=lambda p: p.priority)
            self.ready_queue.remove(highest)
            return highest
        
        else:  # FCFS, Round Robin
            return self.ready_queue.popleft() if self.ready_queue else None
    
    def _calculate_time_slice(self, process: Process) -> float:
        """Calculate time slice for a process."""
        if self.algorithm == CPUSchedulingAlgorithm.ROUND_ROBIN:
            return min(self.time_quantum, process.remaining_time)
        elif self.algorithm == CPUSchedulingAlgorithm.MULTILEVEL_FEEDBACK:
            # Find which queue the process is in
            for i, queue in enumerate(self.mlfq_queues):
                if process in queue:
                    return self.mlfq_quantums[i]
            return self.time_quantum
        else:
            return process.remaining_time
    
    def _should_preempt(self, process: Process, current_time: float) -> bool:
        """Check if current process should be preempted."""
        if process.remaining_time <= 0:
            return True
        
        if self.algorithm == CPUSchedulingAlgorithm.SRTF:
            # Check if a process with shorter remaining time arrived
            if self.ready_queue:
                shortest_ready = min(self.ready_queue, key=lambda p: p.remaining_time)
                if shortest_ready.remaining_time < process.remaining_time:
                    return True
        
        if self.algorithm in [CPUSchedulingAlgorithm.ROUND_ROBIN, CPUSchedulingAlgorithm.MULTILEVEL_FEEDBACK]:
            # Check if time quantum expired
            if process.last_cpu_start:
                elapsed = current_time - process.last_cpu_start
                if elapsed >= self.time_quantum:
                    return True
        
        return False
    
    def _handle_process_preemption(self, process: Process, current_time: float):
        """Handle process preemption or completion."""
        if process.last_cpu_start:
            elapsed = current_time - process.last_cpu_start
            process.cpu_time_used += elapsed
            process.remaining_time -= elapsed
        
        if process.remaining_time <= 0:
            # Process completed
            process.state = ProcessState.TERMINATED
            process.completion_time = current_time
            process.turnaround_time = current_time - process.arrival_time
            self.terminated_processes.append(process)
        else:
            # Return to ready queue
            process.state = ProcessState.READY
            
            if self.algorithm == CPUSchedulingAlgorithm.MULTILEVEL_FEEDBACK:
                # Demote to lower priority queue
                for i in range(len(self.mlfq_queues) - 1):
                    if process in self.mlfq_queues[i] or self._was_in_queue(process, i):
                        self.mlfq_queues[min(i + 1, len(self.mlfq_queues) - 1)].append(process)
                        break
                else:
                    self.mlfq_queues[0].append(process)
            else:
                self.ready_queue.append(process)
    
    def _was_in_queue(self, process: Process, queue_index: int) -> bool:
        """Helper for MLFQ to check previous queue."""
        return False  # Simplified
    
    def execute_io(self, process: Process, io_request: IORequest, current_time: float):
        """Handle I/O completion."""
        io_request.completed = True
        process.io_time_used += io_request.duration
        process.state = ProcessState.READY
        
        if self.algorithm == CPUSchedulingAlgorithm.MULTILEVEL_FEEDBACK:
            # Boost priority after I/O (I/O bound behavior)
            self.mlfq_queues[0].append(process)
        else:
            self.ready_queue.append(process)
    
    def block_for_io(self, process: Process, io_request: IORequest, current_time: float):
        """Block process for I/O."""
        process.state = ProcessState.WAITING
        process.io_requests.append(io_request)
        self.waiting_queue.append(process)
        
        # Free CPU
        for cpu in self.cpus:
            if cpu.current_process == process:
                cpu.current_process = None
                break
    
    def get_statistics(self) -> dict:
        """Get scheduler statistics."""
        if not self.terminated_processes:
            return {
                "total_processes": self.total_processes,
                "completed": 0,
                "avg_turnaround": 0,
                "avg_wait_time": 0,
                "throughput": 0,
                "cpu_utilization": 0
            }
        
        completed = len(self.terminated_processes)
        avg_turnaround = sum(p.turnaround_time for p in self.terminated_processes) / completed
        avg_wait = sum(p.wait_time for p in self.terminated_processes) / completed
        
        total_time = max(p.completion_time for p in self.terminated_processes)
        
        return {
            "total_processes": self.total_processes,
            "completed": completed,
            "avg_turnaround": avg_turnaround,
            "avg_wait_time": avg_wait,
            "throughput": completed / max(1, total_time) * 1000,
            "cpu_utilization": sum(cpu.busy_time for cpu in self.cpus) / max(1, total_time * self.num_cpus)
        }
    
    def get_process_list(self) -> List[Process]:
        """Get list of all processes."""
        return list(self.all_processes.values())
    
    def reset(self):
        """Reset scheduler state."""
        self.ready_queue.clear()
        self.waiting_queue.clear()
        self.all_processes.clear()
        self.terminated_processes.clear()
        self.cpus = [CPU() for _ in range(self.num_cpus)]
        self.total_processes = 0
        self.mlfq_queues = [deque() for _ in range(3)]


class IODeviceManager:
    """
    Manages I/O device operations and queue.
    """
    
    def __init__(self, device_name: str = "disk"):
        self.device_name = device_name
        self.io_queue: deque = deque()
        self.active_operation: Optional[Tuple[Process, IORequest, float]] = None
        self.total_operations = 0
        self.total_time = 0.0
    
    def submit_request(self, process: Process, request: IORequest):
        """Submit an I/O request."""
        self.io_queue.append((process, request))
    
    def tick(self, current_time: float) -> List[Process]:
        """
        Process one time unit of I/O operations.
        Returns list of processes whose I/O completed.
        """
        completed = []
        
        # Check if current operation completed
        if self.active_operation:
            process, request, start_time = self.active_operation
            elapsed = current_time - start_time
            
            if elapsed >= request.duration:
                request.completed = True
                completed.append(process)
                self.total_operations += 1
                self.total_time += elapsed
                self.active_operation = None
        
        # Start next operation if idle
        if not self.active_operation and self.io_queue:
            process, request = self.io_queue.popleft()
            self.active_operation = (process, request, current_time)
        
        return completed
    
    def get_stats(self) -> dict:
        """Get I/O device statistics."""
        return {
            "device": self.device_name,
            "queue_length": len(self.io_queue),
            "total_operations": self.total_operations,
            "avg_io_time": self.total_time / max(1, self.total_operations)
        }


# Example usage
if __name__ == "__main__":
    print("Process Scheduling Simulation")
    print("=" * 50)
    
    scheduler = ProcessScheduler(num_cpus=1, time_quantum=10)
    
    # Create processes
    p1 = scheduler.create_process("browser", 50, process_type=ProcessType.INTERACTIVE)
    p2 = scheduler.create_process("compiler", 100, process_type=ProcessType.CPU_BOUND)
    p3 = scheduler.create_process("editor", 30, process_type=ProcessType.INTERACTIVE)
    
    print(f"\nCreated {scheduler.total_processes} processes")
    
    # Simulate execution
    current_time = 0
    while scheduler.ready_queue or any(cpu.current_process for cpu in scheduler.cpus):
        scheduler.schedule(current_time)
        current_time += 1
    
    stats = scheduler.get_statistics()
    print(f"\nSimulation Results:")
    print(f"Completed: {stats['completed']}")
    print(f"Avg Turnaround: {stats['avg_turnaround']:.2f}ms")
    print(f"Avg Wait Time: {stats['avg_wait_time']:.2f}ms")
    print(f"CPU Utilization: {stats['cpu_utilization']:.2%}")
