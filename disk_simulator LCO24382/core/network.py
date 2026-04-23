"""
Network Stack Simulation Module for OS Core Simulator.
Implements basic TCP/IP stack, packet routing, and socket communication.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set, Callable
from collections import deque
import time
import random
import hashlib


class PacketType(Enum):
    """Types of network packets."""
    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"
    ARP = "arp"
    IP = "ip"


class SocketState(Enum):
    """Socket connection states."""
    CLOSED = "closed"
    LISTEN = "listen"
    SYN_SENT = "syn_sent"
    SYN_RECEIVED = "syn_received"
    ESTABLISHED = "established"
    FIN_WAIT = "fin_wait"
    CLOSE_WAIT = "close_wait"
    CLOSING = "closing"
    LAST_ACK = "last_ack"
    TIME_WAIT = "time_wait"


@dataclass
class IPAddress:
    """IPv4 address representation."""
    address: str  # "192.168.1.1"
    port: int = 0
    
    @classmethod
    def from_string(cls, addr_str: str) -> 'IPAddress':
        """Parse IP address from string."""
        if ':' in addr_str:
            ip, port = addr_str.rsplit(':', 1)
            return cls(ip, int(port))
        return cls(addr_str)
        
    def __str__(self):
        if self.port:
            return f"{self.address}:{self.port}"
        return self.address
        
    def __hash__(self):
        return hash((self.address, self.port))
        
    def __eq__(self, other):
        if isinstance(other, IPAddress):
            return self.address == other.address and self.port == other.port
        return False


@dataclass
class NetworkPacket:
    """Represents a network packet."""
    src_addr: IPAddress
    dst_addr: IPAddress
    packet_type: PacketType
    data: bytes
    ttl: int = 64  # Time to live
    sequence_num: int = 0
    ack_num: int = 0
    flags: Set[str] = field(default_factory=set)  # SYN, ACK, FIN, RST, etc.
    timestamp: float = field(default_factory=time.time)
    id: int = field(default_factory=lambda: int(time.time() * 1000000) % 1000000)
    
    def get_size(self) -> int:
        """Get packet size in bytes."""
        return len(self.data) + 40  # Header + data


@dataclass
class RoutingEntry:
    """Routing table entry."""
    destination: str  # Network address or "default"
    netmask: str
    gateway: Optional[str]
    interface: str
    metric: int = 1


class Socket:
    """
    Socket representation for network communication.
    Implements basic TCP-like behavior.
    """
    
    def __init__(self, socket_id: int, sock_type: PacketType = PacketType.TCP):
        self.socket_id = socket_id
        self.type = sock_type
        self.state = SocketState.CLOSED
        self.local_addr: Optional[IPAddress] = None
        self.remote_addr: Optional[IPAddress] = None
        
        # TCP state
        self.sequence_num = random.randint(0, 10000)
        self.ack_num = 0
        self.receive_buffer: deque = deque(maxlen=100)
        self.send_buffer: deque = deque(maxlen=100)
        self.window_size = 65535
        
        # Statistics
        self.bytes_sent = 0
        self.bytes_received = 0
        self.packets_sent = 0
        self.packets_received = 0
        
    def bind(self, addr: IPAddress) -> bool:
        """Bind socket to local address."""
        self.local_addr = addr
        return True
        
    def listen(self, backlog: int = 5) -> bool:
        """Put socket in listening state."""
        if self.state == SocketState.CLOSED and self.local_addr:
            self.state = SocketState.LISTEN
            return True
        return False
        
    def connect(self, addr: IPAddress) -> bool:
        """Initiate connection to remote address."""
        if self.state == SocketState.CLOSED:
            self.remote_addr = addr
            self.state = SocketState.SYN_SENT
            # Simulate 3-way handshake completion
            self.state = SocketState.ESTABLISHED
            self.sequence_num += 1
            self.ack_num = 1
            return True
        return False
        
    def accept(self) -> Optional['Socket']:
        """Accept incoming connection."""
        if self.state == SocketState.LISTEN:
            # Create new socket for connection
            new_socket = Socket(self.socket_id + 1000, self.type)
            new_socket.local_addr = self.local_addr
            new_socket.state = SocketState.ESTABLISHED
            return new_socket
        return None
        
    def send(self, data: bytes) -> int:
        """Send data through socket."""
        if self.state != SocketState.ESTABLISHED:
            return -1
            
        self.send_buffer.append(data)
        self.bytes_sent += len(data)
        self.packets_sent += 1
        return len(data)
        
    def receive(self, max_size: int = 1024) -> Optional[bytes]:
        """Receive data from socket."""
        if self.state != SocketState.ESTABLISHED:
            return None
            
        if self.receive_buffer:
            data = self.receive_buffer.popleft()
            self.bytes_received += len(data)
            self.packets_received += 1
            return data[:max_size]
        return None
        
    def close(self) -> bool:
        """Close socket connection."""
        if self.state == SocketState.ESTABLISHED:
            self.state = SocketState.FIN_WAIT
            # Simulate close
            self.state = SocketState.CLOSED
        return True
        
    def get_stats(self) -> Dict:
        """Get socket statistics."""
        return {
            'socket_id': self.socket_id,
            'type': self.type.value,
            'state': self.state.value,
            'local_addr': str(self.local_addr) if self.local_addr else None,
            'remote_addr': str(self.remote_addr) if self.remote_addr else None,
            'sequence_num': self.sequence_num,
            'ack_num': self.ack_num,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'packets_sent': self.packets_sent,
            'packets_received': self.packets_received,
            'receive_buffer_size': len(self.receive_buffer),
            'send_buffer_size': len(self.send_buffer)
        }


class NetworkInterface:
    """
    Network interface card (NIC) simulation.
    """
    
    def __init__(self, name: str, mac_address: str, ip_address: IPAddress):
        self.name = name
        self.mac_address = mac_address
        self.ip_address = ip_address
        self.is_up = True
        self.mtu = 1500  # Maximum Transmission Unit
        
        # Statistics
        self.packets_sent = 0
        self.packets_received = 0
        self.bytes_sent = 0
        self.bytes_received = 0
        self.errors = 0
        
        # Packet queue
        self.incoming_queue: deque = deque(maxlen=1000)
        self.outgoing_queue: deque = deque(maxlen=1000)
        
    def send_packet(self, packet: NetworkPacket) -> bool:
        """Send packet through interface."""
        if not self.is_up:
            return False
            
        self.outgoing_queue.append(packet)
        self.packets_sent += 1
        self.bytes_sent += packet.get_size()
        return True
        
    def receive_packet(self, packet: NetworkPacket) -> bool:
        """Receive packet on interface."""
        if not self.is_up:
            return False
            
        self.incoming_queue.append(packet)
        self.packets_received += 1
        self.bytes_received += packet.get_size()
        return True
        
    def get_packet(self) -> Optional[NetworkPacket]:
        """Get packet from incoming queue."""
        return self.incoming_queue.popleft() if self.incoming_queue else None
        
    def get_stats(self) -> Dict:
        """Get interface statistics."""
        return {
            'name': self.name,
            'mac': self.mac_address,
            'ip': str(self.ip_address),
            'is_up': self.is_up,
            'mtu': self.mtu,
            'packets_sent': self.packets_sent,
            'packets_received': self.packets_received,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'errors': self.errors,
            'incoming_queue': len(self.incoming_queue),
            'outgoing_queue': len(self.outgoing_queue)
        }


class Router:
    """
    Network router with routing table.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.interfaces: Dict[str, NetworkInterface] = {}
        self.routing_table: List[RoutingEntry] = []
        self.forwarded_packets = 0
        self.dropped_packets = 0
        
    def add_interface(self, interface: NetworkInterface):
        """Add network interface to router."""
        self.interfaces[interface.name] = interface
        
    def add_route(self, destination: str, netmask: str, 
                  gateway: Optional[str], interface: str, metric: int = 1):
        """Add routing table entry."""
        self.routing_table.append(RoutingEntry(
            destination=destination,
            netmask=netmask,
            gateway=gateway,
            interface=interface,
            metric=metric
        ))
        
    def route_packet(self, packet: NetworkPacket) -> bool:
        """Route packet to appropriate interface."""
        # Find best matching route
        best_route = None
        best_prefix_len = -1
        
        for route in self.routing_table:
            if self._address_in_network(packet.dst_addr.address, 
                                       route.destination, route.netmask):
                prefix_len = self._prefix_length(route.netmask)
                if prefix_len > best_prefix_len:
                    best_prefix_len = prefix_len
                    best_route = route
                    
        if best_route and best_route.interface in self.interfaces:
            iface = self.interfaces[best_route.interface]
            
            # Decrement TTL
            packet.ttl -= 1
            if packet.ttl <= 0:
                self.dropped_packets += 1
                return False
                
            iface.send_packet(packet)
            self.forwarded_packets += 1
            return True
        else:
            self.dropped_packets += 1
            return False
            
    def _address_in_network(self, addr: str, network: str, netmask: str) -> bool:
        """Check if address is in network."""
        if network == "default":
            return True
        # Simplified - would use proper IP math
        return addr.startswith(network.rsplit('.', 1)[0])
        
    def _prefix_length(self, netmask: str) -> int:
        """Get prefix length from netmask."""
        # Simplified
        if netmask == "255.255.255.0":
            return 24
        elif netmask == "255.255.0.0":
            return 16
        elif netmask == "255.0.0.0":
            return 8
        return 0
        
    def get_stats(self) -> Dict:
        """Get router statistics."""
        return {
            'name': self.name,
            'interfaces': {name: iface.get_stats() 
                          for name, iface in self.interfaces.items()},
            'routing_table': [
                {
                    'destination': r.destination,
                    'netmask': r.netmask,
                    'gateway': r.gateway,
                    'interface': r.interface,
                    'metric': r.metric
                }
                for r in self.routing_table
            ],
            'forwarded_packets': self.forwarded_packets,
            'dropped_packets': self.dropped_packets
        }


class NetworkStack:
    """
    Complete network stack manager.
    """
    
    def __init__(self):
        self.interfaces: Dict[str, NetworkInterface] = {}
        self.sockets: Dict[int, Socket] = {}
        self.routers: Dict[str, Router] = {}
        self.next_socket_id = 1
        
        # ARP table
        self.arp_table: Dict[str, str] = {}  # IP -> MAC
        
        # Packet statistics
        self.total_packets = 0
        self.tcp_packets = 0
        self.udp_packets = 0
        self.icmp_packets = 0
        
    def create_interface(self, name: str, mac: str, ip: str, port: int = 0) -> NetworkInterface:
        """Create network interface."""
        ip_addr = IPAddress(ip, port)
        iface = NetworkInterface(name, mac, ip_addr)
        self.interfaces[name] = iface
        self.arp_table[ip] = mac
        return iface
        
    def create_router(self, name: str) -> Router:
        """Create router."""
        router = Router(name)
        self.routers[name] = router
        return router
        
    def create_socket(self, sock_type: PacketType = PacketType.TCP) -> Socket:
        """Create socket."""
        sock = Socket(self.next_socket_id, sock_type)
        self.sockets[self.next_socket_id] = sock
        self.next_socket_id += 1
        return sock
        
    def close_socket(self, socket_id: int) -> bool:
        """Close and remove socket."""
        if socket_id in self.sockets:
            self.sockets[socket_id].close()
            del self.sockets[socket_id]
            return True
        return False
        
    def send_packet(self, src: IPAddress, dst: IPAddress, 
                   data: bytes, packet_type: PacketType = PacketType.TCP) -> bool:
        """Send packet through network."""
        packet = NetworkPacket(
            src_addr=src,
            dst_addr=dst,
            packet_type=packet_type,
            data=data
        )
        
        self.total_packets += 1
        if packet_type == PacketType.TCP:
            self.tcp_packets += 1
        elif packet_type == PacketType.UDP:
            self.udp_packets += 1
        elif packet_type == PacketType.ICMP:
            self.icmp_packets += 1
            
        # Find interface for source address
        for iface in self.interfaces.values():
            if iface.ip_address.address == src.address:
                return iface.send_packet(packet)
                
        return False
        
    def ping(self, src_ip: str, dst_ip: str) -> Dict:
        """Simulate ping (ICMP echo request)."""
        results = {
            'destination': dst_ip,
            'packets_sent': 4,
            'packets_received': 0,
            'packet_loss': 0,
            'min_time': float('inf'),
            'max_time': 0,
            'avg_time': 0,
            'times': []
        }
        
        for i in range(4):
            start_time = time.time()
            
            # Simulate packet transmission
            delay = random.uniform(0.001, 0.050)  # 1-50ms
            time.sleep(delay / 1000)  # Scale for simulation
            
            # Simulate some packet loss
            if random.random() > 0.1:  # 90% success rate
                results['packets_received'] += 1
                elapsed = (time.time() - start_time) * 1000  # ms
                results['times'].append(elapsed)
                results['min_time'] = min(results['min_time'], elapsed)
                results['max_time'] = max(results['max_time'], elapsed)
                
        if results['packets_received'] > 0:
            results['avg_time'] = sum(results['times']) / len(results['times'])
            results['packet_loss'] = (1 - results['packets_received'] / 4) * 100
        else:
            results['min_time'] = 0
            results['avg_time'] = 0
            results['packet_loss'] = 100
            
        return results
        
    def traceroute(self, src_ip: str, dst_ip: str, max_hops: int = 30) -> List[Dict]:
        """Simulate traceroute."""
        hops = []
        
        # Generate intermediate hops
        num_hops = random.randint(3, 8)
        
        for i in range(1, min(num_hops + 1, max_hops)):
            hop_time = random.uniform(1, 50)
            
            # Generate fake intermediate addresses
            if i < num_hops:
                router_ip = f"10.0.{i}.1"
                router_name = f"router-{i}.isp.net"
            else:
                router_ip = dst_ip
                router_name = "destination"
                
            hops.append({
                'hop': i,
                'ip': router_ip,
                'name': router_name,
                'time_ms': round(hop_time, 2),
                'times': [round(hop_time + random.uniform(-2, 2), 2) for _ in range(3)]
            })
            
        return hops
        
    def get_stats(self) -> Dict:
        """Get network statistics."""
        return {
            'total_packets': self.total_packets,
            'tcp_packets': self.tcp_packets,
            'udp_packets': self.udp_packets,
            'icmp_packets': self.icmp_packets,
            'interfaces': {name: iface.get_stats() 
                          for name, iface in self.interfaces.items()},
            'sockets': {sid: sock.get_stats() 
                       for sid, sock in self.sockets.items()},
            'routers': {name: router.get_stats() 
                       for name, router in self.routers.items()},
            'arp_table': self.arp_table
        }
