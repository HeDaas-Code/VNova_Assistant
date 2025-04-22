# -*- coding: utf-8 -*-
"""
Main entry point for the Galgame Story Assistant application.
"""

import sys
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import FluentTranslator, setTheme, Theme

# Import the main window class from the gui module
# Use absolute import based on the project structure
from src.gui.main_window import MainWindow

if __name__ == '__main__':
    # Create the Qt Application
    app = QApplication(sys.argv)
    
    # Apply fluent translator
    translator = FluentTranslator()
    app.installTranslator(translator)
    
    # Set the theme to light (黑字白底)
    setTheme(Theme.LIGHT)

    # Create and show the main window
    mainWin = MainWindow()
    mainWin.show()

    # Run the application's event loop
    sys.exit(app.exec_())