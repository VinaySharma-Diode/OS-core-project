"""
Deadlock Detection and Prevention Module for OS Core Simulator.
Implements Banker's Algorithm, Resource Allocation Graph, and Deadlock Detection.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
import numpy as np


class ResourceType(Enum):
    """Types of system resources."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    PRINTER = "printer"
    NETWORK = "network"
    FILE = "file"


@dataclass
class Resource:
    """Represents a system resource instance."""
    resource_type: ResourceType
    instance_id: int
    allocated_to: Optional[int] = None  # Process ID


@dataclass
class ProcessResourceState:
    """Resource allocation state for a process."""
    process_id: int
    max_demand: Dict[ResourceType, int] = field(default_factory=dict)
    allocated: Dict[ResourceType, int] = field(default_factory=dict)
    needed: Dict[ResourceType, int] = field(default_factory=dict)
    
    def __post_init__(self):
        self.needed = {
            rt: self.max_demand.get(rt, 0) - self.allocated.get(rt, 0)
            for rt in ResourceType
        }


class ResourceAllocationGraph:
    """
    Resource Allocation Graph for deadlock detection.
    Nodes: Processes and Resources
    Edges: Request edges (Process -> Resource) and Assignment edges (Resource -> Process)
    """
    
    def __init__(self):
        self.processes: Set[int] = set()
        self.resources: Dict[Tuple[ResourceType, int], Resource] = {}
        self.request_edges: Dict[int, Set[Tuple[ResourceType, int]]] = defaultdict(set)
        self.assignment_edges: Dict[Tuple[ResourceType, int], Optional[int]] = {}
        
    def add_process(self, pid: int):
        """Add a process node to the graph."""
        self.processes.add(pid)
        
    def add_resource(self, resource_type: ResourceType, instance_id: int):
        """Add a resource instance to the graph."""
        key = (resource_type, instance_id)
        self.resources[key] = Resource(resource_type, instance_id)
        self.assignment_edges[key] = None
        
    def request_resource(self, pid: int, resource_type: ResourceType, instance_id: int):
        """Add a request edge from process to resource."""
        key = (resource_type, instance_id)
        if key in self.resources:
            self.request_edges[pid].add(key)
            
    def allocate_resource(self, pid: int, resource_type: ResourceType, instance_id: int):
        """Allocate resource to process (assignment edge)."""
        key = (resource_type, instance_id)
        if key in self.resources:
            # Remove request edge if exists
            if key in self.request_edges[pid]:
                self.request_edges[pid].remove(key)
            # Add assignment edge
            self.assignment_edges[key] = pid
            self.resources[key].allocated_to = pid
            
    def release_resource(self, resource_type: ResourceType, instance_id: int):
        """Release resource from process."""
        key = (resource_type, instance_id)
        if key in self.resources:
            self.assignment_edges[key] = None
            self.resources[key].allocated_to = None
            
    def detect_deadlock(self) -> Tuple[bool, List[int]]:
        """
        Detect deadlock using cycle detection in resource allocation graph.
        Returns (deadlock_detected, list_of_deadlocked_processes)
        """
        # Build adjacency list: process -> processes it waits for
        waits_for: Dict[int, Set[int]] = defaultdict(set)
        
        for pid in self.processes:
            # Process waits for resources it's requesting
            for resource_key in self.request_edges[pid]:
                # Find who holds this resource
                holder = self.assignment_edges.get(resource_key)
                if holder is not None and holder != pid:
                    waits_for[pid].add(holder)
        
        # Detect cycles using DFS
        deadlocked = set()
        visited = set()
        rec_stack = set()
        
        def dfs(node: int, path: List[int]) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in waits_for[node]:
                if neighbor not in visited:
                    if dfs(neighbor, path + [neighbor]):
                        return True
                elif neighbor in rec_stack:
                    # Cycle found - find all processes in cycle
                    cycle_start = path.index(neighbor) if neighbor in path else 0
                    cycle = path[cycle_start:] + [neighbor]
                    deadlocked.update(cycle)
                    return True
            
            rec_stack.remove(node)
            return False
        
        for pid in self.processes:
            if pid not in visited:
                dfs(pid, [pid])
                
        return len(deadlocked) > 0, list(deadlocked)
    
    def get_graph_data(self) -> Dict:
        """Get graph data for visualization."""
        return {
            'processes': list(self.processes),
            'resources': [
                {
                    'type': rt.value,
                    'instance': inst,
                    'allocated_to': self.assignment_edges.get((rt, inst))
                }
                for (rt, inst) in self.resources.keys()
            ],
            'request_edges': [
                {'from': pid, 'to': {'type': rt.value, 'instance': inst}}
                for pid, resources in self.request_edges.items()
                for (rt, inst) in resources
            ],
            'assignment_edges': [
                {'from': {'type': rt.value, 'instance': inst}, 'to': pid}
                for (rt, inst), pid in self.assignment_edges.items()
                if pid is not None
            ]
        }


class BankersAlgorithm:
    """
    Banker's Algorithm for deadlock avoidance.
    Determines if granting a resource request would leave system in safe state.
    """
    
    def __init__(self, 
                 available: Dict[ResourceType, int],
                 total_resources: Dict[ResourceType, int]):
        self.available = available
        self.total_resources = total_resources
        self.processes: Dict[int, ProcessResourceState] = {}
        self.safety_sequence: List[int] = []
        
    def add_process(self, pid: int, max_demand: Dict[ResourceType, int]):
        """Add a process with its maximum resource demand."""
        self.processes[pid] = ProcessResourceState(
            process_id=pid,
            max_demand=max_demand,
            allocated={rt: 0 for rt in ResourceType}
        )
        
    def allocate(self, pid: int, resource_type: ResourceType, amount: int) -> bool:
        """Allocate resources to a process if safe."""
        if pid not in self.processes:
            return False
            
        process = self.processes[pid]
        
        # Check if request is valid
        if amount > process.needed[resource_type]:
            return False  # Request exceeds maximum claim
            
        if amount > self.available[resource_type]:
            return False  # Not enough resources available
            
        # Try allocation
        self.available[resource_type] -= amount
        process.allocated[resource_type] += amount
        process.needed[resource_type] -= amount
        
        # Check if system is still in safe state
        if self._is_safe_state():
            return True
        else:
            # Rollback
            self.available[resource_type] += amount
            process.allocated[resource_type] -= amount
            process.needed[resource_type] += amount
            return False
            
    def release(self, pid: int, resource_type: ResourceType, amount: int):
        """Release resources from a process."""
        if pid not in self.processes:
            return
            
        process = self.processes[pid]
        process.allocated[resource_type] -= amount
        process.needed[resource_type] += amount
        self.available[resource_type] += amount
        
    def _is_safe_state(self) -> bool:
        """
        Check if current state is safe using safety algorithm.
        Returns True if safe state exists.
        """
        work = self.available.copy()
        finish = {pid: False for pid in self.processes.keys()}
        self.safety_sequence = []
        
        while True:
            found = False
            for pid, process in self.processes.items():
                if not finish[pid]:
                    # Check if process can finish with available resources
                    can_finish = all(
                        process.needed[rt] <= work[rt]
                        for rt in ResourceType
                    )
                    
                    if can_finish:
                        # Process can complete, release its resources
                        for rt in ResourceType:
                            work[rt] += process.allocated[rt]
                        finish[pid] = True
                        self.safety_sequence.append(pid)
                        found = True
                        
            if not found:
                break
                
        return all(finish.values())
    
    def get_state(self) -> Dict:
        """Get current state for visualization."""
        return {
            'available': {rt.value: count for rt, count in self.available.items()},
            'total': {rt.value: count for rt, count in self.total_resources.items()},
            'processes': {
                pid: {
                    'max': {rt.value: count for rt, count in p.max_demand.items()},
                    'allocated': {rt.value: count for rt, count in p.allocated.items()},
                    'needed': {rt.value: count for rt, count in p.needed.items()}
                }
                for pid, p in self.processes.items()
            },
            'safety_sequence': self.safety_sequence,
            'is_safe': self._is_safe_state()
        }


class DeadlockDetector:
    """
    General deadlock detector using wait-for graphs and resource matrices.
    """
    
    def __init__(self):
        self.rag = ResourceAllocationGraph()
        self.bankers: Optional[BankersAlgorithm] = None
        self.detection_history: List[Dict] = []
        
    def setup_bankers(self, available: Dict[ResourceType, int],
                     total: Dict[ResourceType, int]):
        """Setup Banker's algorithm."""
        self.bankers = BankersAlgorithm(available, total)
        
    def check_request_safety(self, pid: int, resource_type: ResourceType, 
                            amount: int) -> Tuple[bool, str]:
        """
        Check if granting a request is safe.
        Returns (is_safe, reason)
        """
        if self.bankers is None:
            return False, "Banker's algorithm not initialized"
            
        if pid not in self.bankers.processes:
            return False, "Process not registered"
            
        process = self.bankers.processes[pid]
        
        if amount > process.needed[resource_type]:
            return False, f"Request exceeds maximum claim ({process.needed[resource_type]} available)"
            
        if amount > self.bankers.available[resource_type]:
            return False, f"Not enough resources available ({self.bankers.available[resource_type]} available)"
            
        # Try allocation and check safety
        if self.bankers.allocate(pid, resource_type, amount):
            return True, "Request granted - system remains in safe state"
        else:
            return False, "Request denied - would lead to unsafe state"
            
    def detect_deadlock(self) -> Tuple[bool, List[int], str]:
        """
        Detect deadlock and return information.
        Returns (deadlock_detected, deadlocked_processes, explanation)
        """
        has_deadlock, processes = self.rag.detect_deadlock()
        
        explanation = ""
        if has_deadlock:
            explanation = f"Deadlock detected! Processes {processes} are deadlocked. "
            explanation += "A cycle exists in the resource allocation graph."
        else:
            explanation = "No deadlock detected. System is in safe state."
            if self.bankers:
                explanation += f" Safety sequence: {self.bankers.safety_sequence}"
                
        # Record in history
        self.detection_history.append({
            'deadlock': has_deadlock,
            'processes': processes,
            'explanation': explanation
        })
        
        return has_deadlock, processes, explanation
    
    def suggest_recovery(self, deadlocked_processes: List[int]) -> List[str]:
        """Suggest recovery strategies for deadlock."""
        suggestions = []
        
        # Process termination
        suggestions.append("1. Process Termination:")
        suggestions.append(f"   - Terminate all deadlocked processes: {deadlocked_processes}")
        suggestions.append(f"   - Or terminate one at a time (victim selection)")
        
        # Resource preemption
        suggestions.append("\n2. Resource Preemption:")
        suggestions.append("   - Select a victim process to preempt resources from")
        suggestions.append("   - Rollback process to safe state")
        suggestions.append("   - Prevent starvation with priority aging")
        
        # Prevention
        suggestions.append("\n3. Deadlock Prevention (future):")
        suggestions.append("   - Use Banker's algorithm for avoidance")
        suggestions.append("   - Implement resource ordering")
        suggestions.append("   - Require processes to request all resources at once")
        
        return suggestions
