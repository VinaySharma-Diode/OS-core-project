"""
Interactive Shell for OS Core Simulator.
Command interpreter with file system, process, and system management commands.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any, Tuple
from collections import deque
import re
import time
from collections import defaultdict


class CommandType(Enum):
    """Types of shell commands."""
    FILE_SYSTEM = "fs"
    PROCESS = "proc"
    MEMORY = "mem"
    DISK = "disk"
    NETWORK = "net"
    SYSTEM = "sys"
    HELP = "help"


@dataclass
class Command:
    """Represents a shell command."""
    name: str
    aliases: List[str]
    category: CommandType
    description: str
    usage: str
    handler: Callable
    args_count: int = 0
    args_optional: bool = False


@dataclass
class CommandHistory:
    """Shell command history entry."""
    command: str
    timestamp: float
    output: str = ""
    exit_code: int = 0


class ShellInterpreter:
    """
    Interactive shell interpreter for OS Core Simulator.
    Provides command-line interface to all system features.
    """
    
    def __init__(self, disk=None, process_scheduler=None, memory_manager=None,
                 sync_manager=None, ipc_manager=None, deadlock_detector=None):
        self.disk = disk
        self.scheduler = process_scheduler
        self.memory = memory_manager
        self.sync_manager = sync_manager
        self.ipc_manager = ipc_manager
        self.deadlock_detector = deadlock_detector
        
        self.commands: Dict[str, Command] = {}
        self.aliases: Dict[str, str] = {}  # alias -> command name
        self.history: deque = deque(maxlen=100)
        self.environment: Dict[str, str] = {
            'PATH': '/bin:/usr/bin',
            'HOME': '/home/user',
            'PWD': '/',
            'USER': 'user',
            'SHELL': 'os_core_shell',
            'PS1': 'os_core$ ',
            'VERBOSE': 'false'
        }
        self.variables: Dict[str, str] = {}
        self.scripts: Dict[str, List[str]] = {}  # Script name -> commands
        
        self._register_default_commands()
        
    def _register_default_commands(self):
        """Register built-in commands."""
        
        # File System Commands
        self.register_command(Command(
            name="ls",
            aliases=["dir", "list"],
            category=CommandType.FILE_SYSTEM,
            description="List directory contents",
            usage="ls [-la] [path]",
            handler=self._cmd_ls,
            args_optional=True
        ))
        
        self.register_command(Command(
            name="cd",
            aliases=["chdir"],
            category=CommandType.FILE_SYSTEM,
            description="Change directory",
            usage="cd <directory>",
            handler=self._cmd_cd,
            args_count=1
        ))
        
        self.register_command(Command(
            name="pwd",
            aliases=["cwd"],
            category=CommandType.FILE_SYSTEM,
            description="Print working directory",
            usage="pwd",
            handler=self._cmd_pwd,
            args_count=0
        ))
        
        self.register_command(Command(
            name="mkdir",
            aliases=["md"],
            category=CommandType.FILE_SYSTEM,
            description="Create directory",
            usage="mkdir <directory>",
            handler=self._cmd_mkdir,
            args_count=1
        ))
        
        self.register_command(Command(
            name="touch",
            aliases=["create", "mkfile"],
            category=CommandType.FILE_SYSTEM,
            description="Create empty file",
            usage="touch <filename> [size]",
            handler=self._cmd_touch,
            args_count=1,
            args_optional=True
        ))
        
        self.register_command(Command(
            name="rm",
            aliases=["del", "delete"],
            category=CommandType.FILE_SYSTEM,
            description="Remove file or directory",
            usage="rm [-r] <path>",
            handler=self._cmd_rm,
            args_count=1,
            args_optional=True
        ))
        
        self.register_command(Command(
            name="cat",
            aliases=["type", "read"],
            category=CommandType.FILE_SYSTEM,
            description="Display file contents",
            usage="cat <filename>",
            handler=self._cmd_cat,
            args_count=1
        ))
        
        # Process Commands
        self.register_command(Command(
            name="ps",
            aliases=["processes", "listproc"],
            category=CommandType.PROCESS,
            description="List processes",
            usage="ps [-a]",
            handler=self._cmd_ps,
            args_optional=True
        ))
        
        self.register_command(Command(
            name="fork",
            aliases=["spawn", "newproc"],
            category=CommandType.PROCESS,
            description="Create new process",
            usage="fork [name] [type]",
            handler=self._cmd_fork,
            args_optional=True
        ))
        
        self.register_command(Command(
            name="kill",
            aliases=["terminate"],
            category=CommandType.PROCESS,
            description="Terminate process",
            usage="kill <pid>",
            handler=self._cmd_kill,
            args_count=1
        ))
        
        self.register_command(Command(
            name="nice",
            aliases=["priority"],
            category=CommandType.PROCESS,
            description="Change process priority",
            usage="nice <pid> <priority>",
            handler=self._cmd_nice,
            args_count=2
        ))
        
        # Memory Commands
        self.register_command(Command(
            name="free",
            aliases=["meminfo", "memory"],
            category=CommandType.MEMORY,
            description="Display memory usage",
            usage="free [-h]",
            handler=self._cmd_free,
            args_optional=True
        ))
        
        self.register_command(Command(
            name="access",
            aliases=["readmem", "page"],
            category=CommandType.MEMORY,
            description="Access memory page",
            usage="access <page_number>",
            handler=self._cmd_access,
            args_count=1
        ))
        
        # Disk Commands
        self.register_command(Command(
            name="df",
            aliases=["diskfree", "diskinfo"],
            category=CommandType.DISK,
            description="Display disk usage",
            usage="df",
            handler=self._cmd_df,
            args_count=0
        ))
        
        self.register_command(Command(
            name="defrag",
            aliases=["optimize"],
            category=CommandType.DISK,
            description="Defragment disk",
            usage="defrag [method]",
            handler=self._cmd_defrag,
            args_optional=True
        ))
        
        self.register_command(Command(
            name="stat",
            aliases=["fileinfo"],
            category=CommandType.DISK,
            description="Display file statistics",
            usage="stat <filename>",
            handler=self._cmd_stat,
            args_count=1
        ))
        
        # System Commands
        self.register_command(Command(
            name="echo",
            aliases=["print"],
            category=CommandType.SYSTEM,
            description="Print text",
            usage="echo <text>",
            handler=self._cmd_echo,
            args_optional=True
        ))
        
        self.register_command(Command(
            name="set",
            aliases=["export"],
            category=CommandType.SYSTEM,
            description="Set environment variable",
            usage="set <variable> <value>",
            handler=self._cmd_set,
            args_count=2
        ))
        
        self.register_command(Command(
            name="env",
            aliases=["environment"],
            category=CommandType.SYSTEM,
            description="Display environment variables",
            usage="env",
            handler=self._cmd_env,
            args_count=0
        ))
        
        self.register_command(Command(
            name="clear",
            aliases=["cls"],
            category=CommandType.SYSTEM,
            description="Clear screen",
            usage="clear",
            handler=self._cmd_clear,
            args_count=0
        ))
        
        self.register_command(Command(
            name="history",
            aliases=["hist"],
            category=CommandType.SYSTEM,
            description="Show command history",
            usage="history [count]",
            handler=self._cmd_history,
            args_optional=True
        ))
        
        self.register_command(Command(
            name="help",
            aliases=["man", "?", "h"],
            category=CommandType.HELP,
            description="Show help",
            usage="help [command]",
            handler=self._cmd_help,
            args_optional=True
        ))
        
        self.register_command(Command(
            name="info",
            aliases=["sysinfo", "status"],
            category=CommandType.SYSTEM,
            description="Show system information",
            usage="info",
            handler=self._cmd_info,
            args_count=0
        ))
        
        self.register_command(Command(
            name="shutdown",
            aliases=["exit", "quit", "logout"],
            category=CommandType.SYSTEM,
            description="Exit shell",
            usage="shutdown",
            handler=self._cmd_shutdown,
            args_count=0
        ))
        
    def register_command(self, cmd: Command):
        """Register a command."""
        self.commands[cmd.name] = cmd
        for alias in cmd.aliases:
            self.aliases[alias] = cmd.name
            
    def execute(self, line: str) -> Tuple[str, int]:
        """Execute a command line. Returns (output, exit_code)."""
        line = line.strip()
        if not line:
            return "", 0
            
        # Parse command and arguments
        parts = self._parse_line(line)
        if not parts:
            return "", 0
            
        cmd_name = parts[0]
        args = parts[1:]
        
        # Resolve alias
        if cmd_name in self.aliases:
            cmd_name = self.aliases[cmd_name]
            
        # Find command
        if cmd_name not in self.commands:
            return f"Error: Command not found: {cmd_name}", 1
            
        cmd = self.commands[cmd_name]
        
        # Check arguments
        if not cmd.args_optional and len(args) < cmd.args_count:
            return f"Error: Usage: {cmd.usage}", 1
            
        # Execute
        try:
            output = cmd.handler(args)
            exit_code = 0
        except Exception as e:
            output = f"Error: {str(e)}"
            exit_code = 1
            
        # Record history
        self.history.append(CommandHistory(
            command=line,
            timestamp=time.time(),
            output=output,
            exit_code=exit_code
        ))
        
        return output, exit_code
        
    def _parse_line(self, line: str) -> List[str]:
        """Parse command line into parts."""
        # Simple parsing - split by spaces but respect quotes
        parts = []
        current = ""
        in_quotes = False
        
        for char in line:
            if char == '"':
                in_quotes = not in_quotes
            elif char == ' ' and not in_quotes:
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += char
                
        if current:
            parts.append(current)
            
        return parts
        
    def get_prompt(self) -> str:
        """Get shell prompt."""
        return self.environment.get('PS1', 'os_core$ ')
        
    def get_completions(self, partial: str) -> List[str]:
        """Get command completions for partial input."""
        completions = []
        
        # Command completions
        for name, cmd in self.commands.items():
            if name.startswith(partial):
                completions.append(name)
            for alias in cmd.aliases:
                if alias.startswith(partial):
                    completions.append(alias)
                    
        # File completions if disk available
        if self.disk and partial:
            try:
                files, dirs = self.disk.ls()
                for f in files:
                    if f.startswith(partial):
                        completions.append(f)
                for d in dirs:
                    if d.startswith(partial):
                        completions.append(d + '/')
            except:
                pass
                
        return completions
        
    def get_history(self, count: int = 20) -> List[CommandHistory]:
        """Get command history."""
        return list(self.history)[-count:]
        
    # ===== Command Handlers =====
    
    def _cmd_ls(self, args: List[str]) -> str:
        """List directory contents."""
        if not self.disk:
            return "Error: Disk not available"
            
        long_format = '-l' in args or '-la' in args
        all_files = '-a' in args or '-la' in args
        
        # Get path if provided
        path = None
        for arg in args:
            if not arg.startswith('-'):
                path = arg
                break
                
        try:
            files, dirs = self.disk.ls()
            
            if not files and not dirs:
                return "Directory is empty"
                
            output = []
            
            if long_format:
                output.append(f"{'Permissions':<12} {'Size':<8} {'Name'}")
                output.append("-" * 40)
                
                for d in dirs:
                    output.append(f"{'drwxr-xr-x':<12} {'<DIR>':<8} {d}/")
                    
                for f in files:
                    meta = self.disk.files.get(f)
                    if meta:
                        size = meta.size
                        perms = meta.permissions
                        output.append(f"{perms:<12} {size:<8} {f}")
                    else:
                        output.append(f"{'-rw-r--r--':<12} {'?':<8} {f}")
            else:
                for d in dirs:
                    output.append(f"{d}/")
                for f in files:
                    output.append(f)
                    
            return '\n'.join(output)
            
        except Exception as e:
            return f"Error: {e}"
            
    def _cmd_cd(self, args: List[str]) -> str:
        """Change directory."""
        if not self.disk:
            return "Error: Disk not available"
            
        path = args[0] if args else "/"
        
        try:
            self.disk.cd(path)
            self.environment['PWD'] = self.disk.pwd()
            return ""
        except Exception as e:
            return f"Error: {e}"
            
    def _cmd_pwd(self, args: List[str]) -> str:
        """Print working directory."""
        if not self.disk:
            return self.environment.get('PWD', '/')
        return self.disk.pwd()
        
    def _cmd_mkdir(self, args: List[str]) -> str:
        """Create directory."""
        if not self.disk:
            return "Error: Disk not available"
            
        name = args[0]
        
        try:
            self.disk.mkdir(name)
            return f"Directory created: {name}"
        except Exception as e:
            return f"Error: {e}"
            
    def _cmd_touch(self, args: List[str]) -> str:
        """Create empty file."""
        if not self.disk:
            return "Error: Disk not available"
            
        name = args[0]
        size = int(args[1]) if len(args) > 1 else 1
        
        try:
            self.disk.create_file(name, size)
            return f"File created: {name} ({size} blocks)"
        except Exception as e:
            return f"Error: {e}"
            
    def _cmd_rm(self, args: List[str]) -> str:
        """Remove file or directory."""
        if not self.disk:
            return "Error: Disk not available"
            
        recursive = '-r' in args
        
        # Get target
        target = None
        for arg in args:
            if not arg.startswith('-'):
                target = arg
                break
                
        if not target:
            return "Error: No target specified"
            
        try:
            self.disk.delete_file(target)
            return f"Removed: {target}"
        except Exception as e:
            return f"Error: {e}"
            
    def _cmd_cat(self, args: List[str]) -> str:
        """Display file contents."""
        if not self.disk:
            return "Error: Disk not available"
            
        name = args[0]
        
        try:
            blocks, read_time = self.disk.read_file(name)
            return f"File: {name}\nBlocks: {blocks}\nRead time: {read_time:.4f}s"
        except Exception as e:
            return f"Error: {e}"
            
    def _cmd_ps(self, args: List[str]) -> str:
        """List processes."""
        if not self.scheduler:
            return "Error: Process scheduler not available"
            
        all_procs = '-a' in args
        stats = self.scheduler.get_statistics()
        
        output = []
        output.append(f"{'PID':<6} {'Name':<12} {'State':<10} {'CPU':<4} {'Priority'}")
        output.append("-" * 50)
        
        for pid, proc in self.scheduler.processes.items():
            cpu_id = proc.assigned_cpu if proc.assigned_cpu is not None else '-'
            output.append(
                f"{pid:<6} {proc.name:<12} {proc.state.value:<10} {str(cpu_id):<4} {proc.priority}"
            )
            
        output.append("")
        output.append(f"Total: {stats['total_processes']} | "
                     f"Ready: {stats['ready_count']} | "
                     f"Running: {stats['running_count']} | "
                     f"Blocked: {stats['blocked_count']}")
        
        return '\n'.join(output)
        
    def _cmd_fork(self, args: List[str]) -> str:
        """Create new process."""
        if not self.scheduler:
            return "Error: Process scheduler not available"
            
        name = args[0] if args else f"Process_{len(self.scheduler.processes)}"
        proc_type = args[1] if len(args) > 1 else "cpu_bound"
        
        from core.process import ProcessType
        ptype = ProcessType(proc_type)
        
        pid = self.scheduler.create_process(name, ptype)
        return f"Created process {name} with PID {pid}"
        
    def _cmd_kill(self, args: List[str]) -> str:
        """Terminate process."""
        if not self.scheduler:
            return "Error: Process scheduler not available"
            
        try:
            pid = int(args[0])
            self.scheduler.terminate_process(pid)
            return f"Process {pid} terminated"
        except Exception as e:
            return f"Error: {e}"
            
    def _cmd_nice(self, args: List[str]) -> str:
        """Change process priority."""
        if not self.scheduler:
            return "Error: Process scheduler not available"
            
        try:
            pid = int(args[0])
            priority = int(args[1])
            # Implementation depends on scheduler API
            return f"Priority of process {pid} set to {priority}"
        except Exception as e:
            return f"Error: {e}"
            
    def _cmd_free(self, args: List[str]) -> str:
        """Display memory usage."""
        if not self.memory:
            return "Error: Memory manager not available"
            
        stats = self.memory.get_stats()
        human_readable = '-h' in args
        
        output = []
        output.append("Memory Usage:")
        output.append(f"  Physical: {stats['used_frames']}/{stats['physical_frames']} frames")
        output.append(f"  Virtual:  {stats['total_virtual_pages']} pages")
        output.append(f"  Page Faults: {stats['page_faults']}")
        output.append(f"  Fault Rate: {stats['page_fault_rate']:.2%}")
        output.append(f"  TLB Hit Rate: {stats['tlb_stats']['hit_rate']:.2%}")
        
        return '\n'.join(output)
        
    def _cmd_access(self, args: List[str]) -> str:
        """Access memory page."""
        if not self.memory:
            return "Error: Memory manager not available"
            
        try:
            page = int(args[0])
            # Assume PID 1 for shell
            frame, is_fault = self.memory.access_page(1, page)
            
            if is_fault:
                return f"Page {page} -> Frame {frame} (PAGE FAULT)"
            else:
                return f"Page {page} -> Frame {frame} (hit)"
        except Exception as e:
            return f"Error: {e}"
            
    def _cmd_df(self, args: List[str]) -> str:
        """Display disk usage."""
        if not self.disk:
            return "Error: Disk not available"
            
        stats = self.disk.get_stats()
        
        output = []
        output.append("Disk Usage:")
        output.append(f"  Total blocks: {stats['total_blocks']}")
        output.append(f"  Used:  {stats['used_blocks']} ({stats['used_blocks']/stats['total_blocks']*100:.1f}%)")
        output.append(f"  Free:  {stats['free_blocks']} ({stats['free_blocks']/stats['total_blocks']*100:.1f}%)")
        output.append(f"  Files: {stats['file_count']}")
        output.append(f"  I/O Operations: {stats['io_operations']}")
        
        return '\n'.join(output)
        
    def _cmd_defrag(self, args: List[str]) -> str:
        """Defragment disk."""
        if not self.disk:
            return "Error: Disk not available"
            
        method = args[0] if args else "basic"
        
        try:
            from core.defragmentation import defragment_basic
            defragment_basic(self.disk)
            return f"Disk defragmented using {method} method"
        except Exception as e:
            return f"Error: {e}"
            
    def _cmd_stat(self, args: List[str]) -> str:
        """Display file statistics."""
        if not self.disk:
            return "Error: Disk not available"
            
        name = args[0]
        
        try:
            if name not in self.disk.files:
                return f"Error: File not found: {name}"
                
            meta = self.disk.files[name]
            blocks = self.disk.get_file_blocks(name)
            
            output = []
            output.append(f"File: {name}")
            output.append(f"  Size: {meta.size} blocks")
            output.append(f"  Blocks: {blocks}")
            output.append(f"  Method: {meta.allocation_method.value}")
            output.append(f"  Permissions: {meta.permissions}")
            output.append(f"  Created: {meta.created}")
            output.append(f"  Modified: {meta.modified}")
            
            return '\n'.join(output)
        except Exception as e:
            return f"Error: {e}"
            
    def _cmd_echo(self, args: List[str]) -> str:
        """Print text."""
        return ' '.join(args)
        
    def _cmd_set(self, args: List[str]) -> str:
        """Set environment variable."""
        var = args[0]
        value = args[1] if len(args) > 1 else ""
        
        self.environment[var] = value
        return f"{var}={value}"
        
    def _cmd_env(self, args: List[str]) -> str:
        """Display environment variables."""
        output = []
        for key, value in sorted(self.environment.items()):
            output.append(f"{key}={value}")
        return '\n'.join(output)
        
    def _cmd_clear(self, args: List[str]) -> str:
        """Clear screen."""
        return "\n" * 50  # Terminal will handle actual clearing
        
    def _cmd_history(self, args: List[str]) -> str:
        """Show command history."""
        count = int(args[0]) if args else 20
        history = self.get_history(count)
        
        output = []
        for i, entry in enumerate(history, 1):
            output.append(f"{i:4}  {entry.command}")
            
        return '\n'.join(output)
        
    def _cmd_help(self, args: List[str]) -> str:
        """Show help."""
        if args:
            # Help for specific command
            cmd_name = args[0]
            if cmd_name in self.aliases:
                cmd_name = self.aliases[cmd_name]
                
            if cmd_name in self.commands:
                cmd = self.commands[cmd_name]
                return (
                    f"{cmd.name} - {cmd.description}\n"
                    f"Usage: {cmd.usage}\n"
                    f"Aliases: {', '.join(cmd.aliases)}\n"
                    f"Category: {cmd.category.value}"
                )
            else:
                return f"Unknown command: {cmd_name}"
        else:
            # General help
            output = []
            output.append("OS Core Simulator Shell Commands")
            output.append("=" * 40)
            output.append("")
            
            categories = {}
            for cmd in self.commands.values():
                cat = cmd.category
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(cmd)
                
            for cat in sorted(categories.keys(), key=lambda c: c.value):
                output.append(f"\n[{cat.value.upper()}]")
                for cmd in sorted(categories[cat], key=lambda c: c.name):
                    output.append(f"  {cmd.name:<12} - {cmd.description}")
                    
            output.append("")
            output.append("Use 'help <command>' for detailed information")
            
            return '\n'.join(output)
            
    def _cmd_info(self, args: List[str]) -> str:
        """Show system information."""
        output = []
        output.append("OS Core Simulator")
        output.append("=" * 30)
        output.append("")
        output.append("Subsystems:")
        output.append(f"  Disk:       {'✓' if self.disk else '✗'}")
        output.append(f"  Processes:  {'✓' if self.scheduler else '✗'}")
        output.append(f"  Memory:     {'✓' if self.memory else '✗'}")
        output.append(f"  Sync:       {'✓' if self.sync_manager else '✗'}")
        output.append(f"  IPC:        {'✓' if self.ipc_manager else '✗'}")
        output.append(f"  Deadlock:   {'✓' if self.deadlock_detector else '✗'}")
        output.append("")
        output.append(f"Commands: {len(self.commands)}")
        output.append(f"Variables: {len(self.environment)}")
        
        return '\n'.join(output)
        
    def _cmd_shutdown(self, args: List[str]) -> str:
        """Exit shell."""
        return "SHUTDOWN"
