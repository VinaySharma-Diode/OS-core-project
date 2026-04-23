"""
Security and Access Control Module for OS Core Simulator.
Implements authentication, authorization, permissions, and encryption.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Callable, Tuple
from collections import defaultdict
import hashlib
import secrets
import time
from collections import deque


class Permission(Enum):
    """File and resource permissions."""
    READ = 0b100
    WRITE = 0b010
    EXECUTE = 0b001
    

class UserRole(Enum):
    """User roles with different privilege levels."""
    ROOT = "root"           # Full system access
    ADMIN = "admin"         # Administrative access
    USER = "user"           # Regular user
    GUEST = "guest"         # Limited access
    SERVICE = "service"     # Service account


@dataclass
class User:
    """System user account."""
    username: str
    uid: int
    gid: int
    role: UserRole
    home_directory: str
    shell: str = "/bin/bash"
    password_hash: str = ""
    salt: str = ""
    created: float = field(default_factory=time.time)
    last_login: Optional[float] = None
    failed_logins: int = 0
    locked: bool = False
    groups: List[int] = field(default_factory=list)
    
    def set_password(self, password: str):
        """Hash and set password."""
        self.salt = secrets.token_hex(16)
        self.password_hash = hashlib.sha256(
            (password + self.salt).encode()
        ).hexdigest()
        
    def verify_password(self, password: str) -> bool:
        """Verify password against hash."""
        if not self.password_hash or not self.salt:
            return False
        test_hash = hashlib.sha256(
            (password + self.salt).encode()
        ).hexdigest()
        return test_hash == self.password_hash


@dataclass
class Group:
    """User group."""
    name: str
    gid: int
    members: List[int] = field(default_factory=list)  # UIDs


@dataclass
class ACL:
    """Access Control List entry."""
    owner: int  # UID
    group: int  # GID
    owner_perms: int = 0b110  # rw-
    group_perms: int = 0b100  # r--
    other_perms: int = 0b100  # r--
    
    def check_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has specific permission."""
        perm_value = permission.value
        
        # Owner check
        if user.uid == self.owner:
            return bool(self.owner_perms & perm_value)
            
        # Group check
        if user.gid == self.group or self.group in user.groups:
            return bool(self.group_perms & perm_value)
            
        # Other check
        return bool(self.other_perms & perm_value)
        
    def set_permission(self, target: str, permission: Permission, grant: bool):
        """Set permission for target (owner/group/other)."""
        perm_value = permission.value if grant else 0
        
        if target == "owner":
            if grant:
                self.owner_perms |= perm_value
            else:
                self.owner_perms &= ~perm_value
        elif target == "group":
            if grant:
                self.group_perms |= perm_value
            else:
                self.group_perms &= ~perm_value
        elif target == "other":
            if grant:
                self.other_perms |= perm_value
            else:
                self.other_perms &= ~perm_value
                
    def to_string(self) -> str:
        """Convert to Unix-style permission string."""
        def perm_bits_to_str(bits: int) -> str:
            r = 'r' if bits & 0b100 else '-'
            w = 'w' if bits & 0b010 else '-'
            x = 'x' if bits & 0b001 else '-'
            return r + w + x
            
        return perm_bits_to_str(self.owner_perms) + \
               perm_bits_to_str(self.group_perms) + \
               perm_bits_to_str(self.other_perms)


@dataclass
class SecurityPolicy:
    """System security policy settings."""
    min_password_length: int = 8
    password_require_uppercase: bool = True
    password_require_numbers: bool = True
    password_require_special: bool = True
    max_failed_logins: int = 3
    lockout_duration: int = 300  # seconds
    password_expiry_days: int = 90
    session_timeout: int = 3600  # seconds
    require_sudo_password: bool = True
    audit_enabled: bool = True


@dataclass
class AuditEvent:
    """Security audit log entry."""
    timestamp: float
    event_type: str
    user: str
    resource: str
    action: str
    success: bool
    details: str = ""


class AuthenticationManager:
    """
    User authentication and session management.
    """
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.groups: Dict[str, Group] = {}
        self.sessions: Dict[str, Dict] = {}  # session_id -> session info
        self.current_user: Optional[User] = None
        self.policy = SecurityPolicy()
        self.audit_log: deque = deque(maxlen=1000)
        
        # Create default users
        self._create_default_users()
        
    def _create_default_users(self):
        """Create default system users."""
        # Root user
        root = User(
            username="root",
            uid=0,
            gid=0,
            role=UserRole.ROOT,
            home_directory="/root",
            shell="/bin/bash"
        )
        root.set_password("root")
        self.users["root"] = root
        
        # Regular user
        user = User(
            username="user",
            uid=1000,
            gid=1000,
            role=UserRole.USER,
            home_directory="/home/user",
            shell="/bin/bash"
        )
        user.set_password("user")
        self.users["user"] = user
        
        # Guest user
        guest = User(
            username="guest",
            uid=1001,
            gid=1001,
            role=UserRole.GUEST,
            home_directory="/tmp",
            shell="/bin/sh"
        )
        guest.set_password("guest")
        self.users["guest"] = guest
        
        # Create default groups
        self.groups["root"] = Group("root", 0, [0])
        self.groups["users"] = Group("users", 1000, [1000, 1001])
        self.groups["guests"] = Group("guests", 1001, [1001])
        
    def authenticate(self, username: str, password: str) -> Tuple[bool, str]:
        """Authenticate user with password."""
        if username not in self.users:
            self._audit("AUTH", username, "login", False, "User not found")
            return False, "Invalid username or password"
            
        user = self.users[username]
        
        if user.locked:
            self._audit("AUTH", username, "login", False, "Account locked")
            return False, "Account is locked due to too many failed attempts"
            
        if user.verify_password(password):
            user.failed_logins = 0
            user.last_login = time.time()
            self.current_user = user
            
            # Create session
            session_id = secrets.token_hex(16)
            self.sessions[session_id] = {
                'user': username,
                'uid': user.uid,
                'start_time': time.time(),
                'last_activity': time.time()
            }
            
            self._audit("AUTH", username, "login", True, f"Session: {session_id}")
            return True, session_id
        else:
            user.failed_logins += 1
            
            if user.failed_logins >= self.policy.max_failed_logins:
                user.locked = True
                self._audit("AUTH", username, "login", False, "Account locked")
                return False, "Account locked due to too many failed attempts"
                
            self._audit("AUTH", username, "login", False, 
                       f"Failed attempt {user.failed_logins}")
            return False, "Invalid username or password"
            
    def logout(self, session_id: str):
        """End user session."""
        if session_id in self.sessions:
            user = self.sessions[session_id]['user']
            del self.sessions[session_id]
            self._audit("AUTH", user, "logout", True, "")
            
        if self.current_user and self.current_user.username not in [
            s['user'] for s in self.sessions.values()
        ]:
            self.current_user = None
            
    def check_authorization(self, resource: str, action: Permission) -> bool:
        """Check if current user can perform action on resource."""
        if not self.current_user:
            return False
            
        # Root can do anything
        if self.current_user.role == UserRole.ROOT:
            return True
            
        # Get ACL for resource (simplified)
        acl = self._get_resource_acl(resource)
        if acl:
            return acl.check_permission(self.current_user, action)
            
        return False
        
    def _get_resource_acl(self, resource: str) -> Optional[ACL]:
        """Get ACL for resource (placeholder)."""
        # In real implementation, would look up from file system
        return ACL(
            owner=self.current_user.uid if self.current_user else 0,
            group=self.current_user.gid if self.current_user else 0
        )
        
    def _audit(self, event_type: str, user: str, action: str, 
               success: bool, details: str):
        """Record audit event."""
        if not self.policy.audit_enabled:
            return
            
        event = AuditEvent(
            timestamp=time.time(),
            event_type=event_type,
            user=user,
            resource="system",
            action=action,
            success=success,
            details=details
        )
        self.audit_log.append(event)
        
    def add_user(self, username: str, uid: int, gid: int, 
                 role: UserRole, password: str) -> bool:
        """Add new user to system."""
        if username in self.users:
            return False
            
        if not self._validate_password(password):
            return False
            
        user = User(
            username=username,
            uid=uid,
            gid=gid,
            role=role,
            home_directory=f"/home/{username}"
        )
        user.set_password(password)
        self.users[username] = user
        
        self._audit("USER", self.current_user.username if self.current_user else "system",
                   "add_user", True, f"Created user {username}")
        return True
        
    def _validate_password(self, password: str) -> bool:
        """Validate password against policy."""
        if len(password) < self.policy.min_password_length:
            return False
            
        if self.policy.password_require_uppercase and not any(c.isupper() for c in password):
            return False
            
        if self.policy.password_require_numbers and not any(c.isdigit() for c in password):
            return False
            
        if self.policy.password_require_special:
            special = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            if not any(c in special for c in password):
                return False
                
        return True
        
    def get_audit_log(self, count: int = 100) -> List[AuditEvent]:
        """Get recent audit log entries."""
        return list(self.audit_log)[-count:]
        
    def get_user_info(self, username: str) -> Optional[Dict]:
        """Get user information."""
        if username not in self.users:
            return None
            
        user = self.users[username]
        return {
            'username': user.username,
            'uid': user.uid,
            'gid': user.gid,
            'role': user.role.value,
            'home': user.home_directory,
            'shell': user.shell,
            'created': user.created,
            'last_login': user.last_login,
            'locked': user.locked,
            'groups': user.groups
        }


class EncryptionManager:
    """
    Simple encryption/decryption simulation.
    (Note: Not cryptographically secure - for educational purposes only)
    """
    
    def __init__(self):
        self.keys: Dict[str, bytes] = {}
        
    def generate_key(self, name: str) -> bytes:
        """Generate encryption key."""
        key = secrets.token_bytes(32)
        self.keys[name] = key
        return key
        
    def encrypt(self, data: bytes, key_name: str) -> bytes:
        """Encrypt data using XOR with key (simplified)."""
        if key_name not in self.keys:
            raise ValueError(f"Key not found: {key_name}")
            
        key = self.keys[key_name]
        # Simple XOR encryption (educational only)
        encrypted = bytearray()
        for i, byte in enumerate(data):
            encrypted.append(byte ^ key[i % len(key)])
        return bytes(encrypted)
        
    def decrypt(self, data: bytes, key_name: str) -> bytes:
        """Decrypt data (XOR is symmetric)."""
        # XOR is its own inverse
        return self.encrypt(data, key_name)
        
    def hash(self, data: bytes) -> str:
        """Calculate SHA-256 hash."""
        return hashlib.sha256(data).hexdigest()


class CapabilityManager:
    """
    Capability-based access control.
    Fine-grained privileges for processes.
    """
    
    def __init__(self):
        self.capabilities: Dict[int, Set[str]] = {}  # pid -> capabilities
        self.all_capabilities = {
            'CAP_CHOWN',      # Change file ownership
            'CAP_KILL',       # Send signals to any process
            'CAP_SETUID',     # Change process UID
            'CAP_SETGID',     # Change process GID
            'CAP_NET_ADMIN',  # Network administration
            'CAP_SYS_ADMIN',  # System administration
            'CAP_SYS_PTRACE', # Trace any process
            'CAP_SYS_BOOT',   # Reboot system
            'CAP_MKNOD',      # Create special files
            'CAP_DAC_READ_SEARCH',  # Bypass file read/execute checks
            'CAP_DAC_OVERRIDE',       # Bypass file read/write/execute checks
        }
        
    def grant_capability(self, pid: int, capability: str) -> bool:
        """Grant capability to process."""
        if capability not in self.all_capabilities:
            return False
            
        if pid not in self.capabilities:
            self.capabilities[pid] = set()
            
        self.capabilities[pid].add(capability)
        return True
        
    def revoke_capability(self, pid: int, capability: str) -> bool:
        """Revoke capability from process."""
        if pid in self.capabilities:
            self.capabilities[pid].discard(capability)
            return True
        return False
        
    def check_capability(self, pid: int, capability: str) -> bool:
        """Check if process has capability."""
        if pid in self.capabilities:
            return capability in self.capabilities[pid]
        return False
        
    def drop_all_capabilities(self, pid: int):
        """Drop all capabilities (privilege reduction)."""
        if pid in self.capabilities:
            self.capabilities[pid].clear()
            
    def get_process_capabilities(self, pid: int) -> Set[str]:
        """Get all capabilities for process."""
        return self.capabilities.get(pid, set()).copy()


class SecurityManager:
    """
    Central security manager combining all security features.
    """
    
    def __init__(self):
        self.auth = AuthenticationManager()
        self.encryption = EncryptionManager()
        self.capabilities = CapabilityManager()
        
    def login(self, username: str, password: str) -> Tuple[bool, str]:
        """Authenticate and start session."""
        return self.auth.authenticate(username, password)
        
    def logout(self, session_id: str):
        """End session."""
        self.auth.logout(session_id)
        
    def check_access(self, resource: str, action: Permission) -> bool:
        """Check access permission."""
        return self.auth.check_authorization(resource, action)
        
    def sudo(self, password: str) -> bool:
        """Elevate privileges (simplified sudo)."""
        if not self.auth.current_user:
            return False
            
        # Verify current user's password
        if self.auth.current_user.verify_password(password):
            # Grant temporary root capabilities
            return True
        return False
        
    def get_stats(self) -> Dict:
        """Get security statistics."""
        return {
            'users': len(self.auth.users),
            'groups': len(self.auth.groups),
            'active_sessions': len(self.auth.sessions),
            'current_user': self.auth.current_user.username if self.auth.current_user else None,
            'audit_entries': len(self.auth.audit_log),
            'keys': len(self.encryption.keys),
            'capabilities_granted': sum(len(caps) for caps in self.capabilities.capabilities.values())
        }
