"""
Interactive Shell Terminal View for OS Core Simulator.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QLineEdit, QPushButton, QComboBox,
    QCompleter, QListWidget, QListWidgetItem, QSplitter,
    QGroupBox, QGridLayout, QFrame
)
from PyQt5.QtCore import Qt, QStringListModel
from PyQt5.QtGui import QFont, QColor, QTextCharFormat, QKeyEvent

from core.shell import ShellInterpreter
from core.disk import Disk
from core.process import ProcessScheduler
from core.memory import MemoryManager


class TerminalWidget(QTextEdit):
    """Custom terminal widget with command history."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Consolas", 11))
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: none;
                padding: 10px;
            }
        """)
        self.setReadOnly(True)
        
        # ANSI color support
        self.colors = {
            'reset': '\033[0m',
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'magenta': '\033[95m',
            'cyan': '\033[96m',
            'white': '\033[97m',
        }
        
    def append_output(self, text: str, color: str = None):
        """Append colored text to terminal."""
        if color and color in self.colors:
            # Store color info for the text
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            self.setCurrentCharFormat(fmt)
            
        self.append(text)
        
        # Reset format
        fmt = QTextCharFormat()
        fmt.setForeground(QColor('#d4d4d4'))
        self.setCurrentCharFormat(fmt)
        
        # Auto-scroll
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


class CommandInput(QLineEdit):
    """Command input with history and tab completion."""
    
    command_history = []
    history_index = -1
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Consolas", 11))
        self.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 2px solid #3c3c3c;
                border-radius: 4px;
                padding: 8px;
            }
            QLineEdit:focus {
                border-color: #007acc;
            }
        """)
        self.setPlaceholderText("Enter command...")
        
    def keyPressEvent(self, event: QKeyEvent):
        """Handle special keys."""
        if event.key() == Qt.Key_Up:
            self.navigate_history(-1)
        elif event.key() == Qt.Key_Down:
            self.navigate_history(1)
        elif event.key() == Qt.Key_Tab:
            self.request_completion()
        else:
            super().keyPressEvent(event)
            
    def navigate_history(self, direction: int):
        """Navigate command history."""
        if not self.command_history:
            return
            
        self.history_index += direction
        self.history_index = max(0, min(self.history_index, len(self.command_history) - 1))
        
        if 0 <= self.history_index < len(self.command_history):
            self.setText(self.command_history[self.history_index])
            
    def request_completion(self):
        """Request command completion."""
        # Will be connected to shell's completion
        pass
        
    def add_to_history(self, cmd: str):
        """Add command to history."""
        if cmd and cmd not in self.command_history:
            self.command_history.append(cmd)
        self.history_index = len(self.command_history)


class ShellView(QWidget):
    """
    Interactive shell terminal view.
    Provides command-line interface to the OS simulator.
    """
    
    def __init__(self):
        super().__init__()
        
        # Create shell interpreter
        self.disk = Disk(size=64)
        self.scheduler = ProcessScheduler(num_cpus=2)
        self.memory = MemoryManager(physical_memory_size=32)
        
        self.shell = ShellInterpreter(
            disk=self.disk,
            process_scheduler=self.scheduler,
            memory_manager=self.memory
        )
        
        self.init_ui()
        self.init_sample_data()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Top bar with info
        top_bar = QFrame()
        top_bar.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border-bottom: 1px solid #3c3c3c;
                padding: 5px;
            }
        """)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(10, 5, 10, 5)
        
        self.lbl_user = QLabel("user@os_core")
        self.lbl_user.setStyleSheet("color: #4ec9b0;")
        top_layout.addWidget(self.lbl_user)
        
        self.lbl_pwd = QLabel("~/")
        self.lbl_pwd.setStyleSheet("color: #dcdcaa;")
        top_layout.addWidget(self.lbl_pwd)
        
        top_layout.addStretch()
        
        self.lbl_status = QLabel("✓ Ready")
        self.lbl_status.setStyleSheet("color: #4caf50;")
        top_layout.addWidget(self.lbl_status)
        
        layout.addWidget(top_bar)
        
        # Main content splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Terminal area
        terminal_container = QWidget()
        terminal_layout = QVBoxLayout(terminal_container)
        terminal_layout.setContentsMargins(0, 0, 0, 0)
        terminal_layout.setSpacing(0)
        
        # Terminal output
        self.terminal = TerminalWidget()
        terminal_layout.addWidget(self.terminal)
        
        # Input area
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(5, 5, 5, 5)
        input_layout.setSpacing(5)
        
        prompt = QLabel("$")
        prompt.setFont(QFont("Consolas", 11))
        prompt.setStyleSheet("color: #4ec9b0;")
        input_layout.addWidget(prompt)
        
        self.command_input = CommandInput()
        self.command_input.returnPressed.connect(self.execute_command)
        input_layout.addWidget(self.command_input)
        
        btn_execute = QPushButton("▶")
        btn_execute.setFixedWidth(30)
        btn_execute.clicked.connect(self.execute_command)
        input_layout.addWidget(btn_execute)
        
        terminal_layout.addWidget(input_container)
        
        splitter.addWidget(terminal_container)
        
        # Side panel
        side_panel = QWidget()
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(5, 5, 5, 5)
        
        # Quick commands
        quick_group = QGroupBox("Quick Commands")
        quick_layout = QVBoxLayout()
        
        quick_commands = [
            ("ls -la", "List files"),
            ("ps", "List processes"),
            ("free", "Memory info"),
            ("df", "Disk usage"),
            ("help", "Show help"),
            ("info", "System info"),
            ("clear", "Clear screen"),
        ]
        
        for cmd, desc in quick_commands:
            btn = QPushButton(f"{cmd}")
            btn.setToolTip(desc)
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 5px;
                    background-color: #2d2d2d;
                    border: 1px solid #3c3c3c;
                    color: #d4d4d4;
                }
                QPushButton:hover {
                    background-color: #3c3c3c;
                }
            """)
            btn.clicked.connect(lambda checked, c=cmd: self.run_quick_command(c))
            quick_layout.addWidget(btn)
            
        quick_group.setLayout(quick_layout)
        side_layout.addWidget(quick_group)
        
        # Command history
        history_group = QGroupBox("Command History")
        history_layout = QVBoxLayout()
        
        self.history_list = QListWidget()
        self.history_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
            }
            QListWidget::item:hover {
                background-color: #2d2d2d;
            }
        """)
        self.history_list.itemClicked.connect(self.on_history_clicked)
        history_layout.addWidget(self.history_list)
        
        btn_clear_history = QPushButton("Clear History")
        btn_clear_history.clicked.connect(self.clear_history)
        history_layout.addWidget(btn_clear_history)
        
        history_group.setLayout(history_layout)
        side_layout.addWidget(history_group)
        
        # Environment variables
        env_group = QGroupBox("Environment")
        env_layout = QVBoxLayout()
        
        self.env_list = QListWidget()
        self.env_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                font-family: Consolas;
                font-size: 10px;
            }
        """)
        env_layout.addWidget(self.env_list)
        
        btn_refresh_env = QPushButton("Refresh")
        btn_refresh_env.clicked.connect(self.update_env_list)
        env_layout.addWidget(btn_refresh_env)
        
        env_group.setLayout(env_layout)
        side_layout.addWidget(env_group)
        
        side_layout.addStretch()
        
        splitter.addWidget(side_panel)
        splitter.setSizes([600, 200])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
        
        # Print welcome message
        self.show_welcome()
        self.update_env_list()
        
    def init_sample_data(self):
        """Initialize sample data for demonstration."""
        # Create some sample files
        try:
            self.disk.mkdir("documents")
            self.disk.mkdir("downloads")
            self.disk.create_file("readme.txt", 2)
            self.disk.create_file("data.dat", 5)
            
            # Create some processes
            from core.process import ProcessType
            self.scheduler.create_process("shell", ProcessType.INTERACTIVE)
            self.scheduler.create_process("editor", ProcessType.INTERACTIVE)
            self.scheduler.create_process("logger", ProcessType.IO_BOUND)
            
        except Exception as e:
            pass
            
    def show_welcome(self):
        """Display welcome message."""
        welcome = """
╔══════════════════════════════════════════════════════════════╗
║           OS Core Simulator - Interactive Shell              ║
║                                                              ║
║  Type 'help' for available commands                         ║
║  Type 'info' for system information                         ║
╚══════════════════════════════════════════════════════════════╝
        """
        self.terminal.append_output(welcome, "cyan")
        self.terminal.append_output("")
        
    def execute_command(self):
        """Execute command from input."""
        cmd = self.command_input.text().strip()
        if not cmd:
            return
            
        # Add to input history
        self.command_input.add_to_history(cmd)
        
        # Show command in terminal
        prompt = f"$ {cmd}"
        self.terminal.append_output(prompt, "green")
        
        # Execute
        try:
            output, exit_code = self.shell.execute(cmd)
            
            if output:
                if output == "SHUTDOWN":
                    self.terminal.append_output("Shutting down...", "yellow")
                    # Don't actually close, just simulate
                    self.terminal.append_output("Session terminated. Type 'help' to continue.")
                else:
                    self.terminal.append_output(output)
                    
            # Update status
            if exit_code == 0:
                self.lbl_status.setText("✓ Success")
                self.lbl_status.setStyleSheet("color: #4caf50;")
            else:
                self.lbl_status.setText(f"✗ Error {exit_code}")
                self.lbl_status.setStyleSheet("color: #f44336;")
                
            # Add to history list
            item = QListWidgetItem(f"$ {cmd}")
            if exit_code != 0:
                item.setForeground(QColor('#f44336'))
            self.history_list.insertItem(0, item)
            
            # Update environment
            self.update_env_list()
            self.update_pwd()
            
        except Exception as e:
            self.terminal.append_output(f"Error: {str(e)}", "red")
            self.lbl_status.setText("✗ Exception")
            self.lbl_status.setStyleSheet("color: #f44336;")
            
        # Clear input
        self.command_input.clear()
        self.command_input.setFocus()
        
    def run_quick_command(self, cmd: str):
        """Run a quick command."""
        self.command_input.setText(cmd)
        self.execute_command()
        
    def on_history_clicked(self, item: QListWidgetItem):
        """Handle history item click."""
        text = item.text()
        if text.startswith("$ "):
            text = text[2:]
        self.command_input.setText(text)
        
    def clear_history(self):
        """Clear command history."""
        self.history_list.clear()
        self.command_input.command_history.clear()
        
    def update_env_list(self):
        """Update environment variables display."""
        self.env_list.clear()
        for key, value in sorted(self.shell.environment.items()):
            item = QListWidgetItem(f"{key}={value}")
            item.setForeground(QColor('#9cdcfe'))
            self.env_list.addItem(item)
            
    def update_pwd(self):
        """Update current directory display."""
        pwd = self.shell.environment.get('PWD', '/')
        self.lbl_pwd.setText(pwd)
