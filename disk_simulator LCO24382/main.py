import sys
from PyQt5.QtWidgets import QApplication
from ui.dashboard import Dashboard
from ui.styles import apply_dark_theme

def main():
    """
    Entry point for the Disk Fragmentation Simulator.
    Initializes the PyQt5 application, applies dark theme, and launches the dashboard.
    """
    app = QApplication(sys.argv)

    # Apply dark mode theme
    apply_dark_theme(app)

    # Create and show main dashboard window
    window = Dashboard()
    window.show()

    # Run event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
