import sys
import re
import time
import threading
import queue
import pyautogui
import speech_recognition as sr

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtCore import Qt, QRectF

# --- Global Constants ---
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
NUM_COLUMNS = 26  # A-Z
NUM_ROWS = 50     # 1-50

CELL_WIDTH = SCREEN_WIDTH / NUM_COLUMNS
CELL_HEIGHT = SCREEN_HEIGHT / NUM_ROWS

# New options for colors (RGBA format)
GRID_LINE_COLOR = (255, 255, 0, 150)  # Yellow with transparency
TEXT_COLOR = (255, 255, 255, 200)     # White with transparency

# Global variable to hold the main window reference for UI control
main_window = None

# Thread-safe queue for commands from speech recognition
command_queue = queue.Queue()

# --- Voice Recognition Thread ---
def voice_command_listener():
    """Continuously listens for voice commands and enqueues them."""
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    # Calibrate for ambient noise
    with microphone as source:
        print("Calibrating microphone...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
    
    while True:
        try:
            with microphone as source:
                print("Listening for command...")
                audio = recognizer.listen(source, timeout=5)
            # Use Google Web Speech API (or change to your preferred engine)
            command = recognizer.recognize_google(audio)
            print("Command received:", command)
            command_queue.put(command.lower())
        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            print("Could not understand audio")
        except sr.RequestError as e:
            print("Request error:", e)
        time.sleep(0.5)

def process_command(command):
    """
    Process a command.
    Supported formats include:
      - "move to b3"
      - "left click", "double click", "right click"
      - "scroll up", "scroll down"
      - "type this <text>"
      - "hide grid", "show grid"
      - "press left/right/up/down"
    """
    global main_window
    command = command.strip().lower()
    
    if command.startswith("move to"):
        remainder = command[len("move to"):].strip()
        match = re.fullmatch(r"([a-z])\s*(\d{1,2})", remainder)
        if match:
            letter = match.group(1).upper()
            number = int(match.group(2))
            if not ('A' <= letter <= 'Z') or not (1 <= number <= NUM_ROWS):
                print("Command out of grid range:", command)
                return
            col_index = ord(letter) - ord('A')
            row_index = number - 1
            x = col_index * CELL_WIDTH + CELL_WIDTH / 2
            y = row_index * CELL_HEIGHT + CELL_HEIGHT / 2
            print(f"Moving mouse to cell {letter}{number} at ({x:.0f}, {y:.0f})")
            pyautogui.moveTo(x, y)
        else:
            print("Invalid move command format:", command)
    elif "left click" in command:
        print("Performing left click")
        pyautogui.click()
    elif "double click" in command:
        print("Performing double click")
        pyautogui.doubleClick()
    elif "right click" in command:
        print("Performing right click")
        pyautogui.rightClick()
    elif "scroll up" in command:
        print("Scrolling up")
        pyautogui.scroll(222)
    elif "scroll down" in command:
        print("Scrolling down")
        pyautogui.scroll(-222)
    elif command.startswith("type this"):
        text = command[len("type this"):].strip()
        print(f"Typing: {text}")
        pyautogui.write(text)
    elif command == "hide grid":
        print("Hiding grid overlay")
        if main_window:
            main_window.grid_widget.hide()
    elif command == "show grid":
        print("Showing grid overlay")
        if main_window:
            main_window.grid_widget.show()
    elif command.startswith("press "):
        arrow = command[len("press "):].strip()
        if arrow in ["left", "right", "up", "down"]:
            print(f"Pressing {arrow} arrow")
            pyautogui.press(arrow)
        else:
            print("Unrecognized arrow command:", command)
    else:
        print("Unrecognized command:", command)

# --- PySide6 Grid Widget ---
class GridWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Set the widget to have a transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Use configured grid line color
        grid_color = QColor(*GRID_LINE_COLOR)
        pen = QPen(grid_color)
        pen.setWidth(1)
        painter.setPen(pen)
        
        # Draw vertical grid lines
        for col in range(NUM_COLUMNS + 1):
            x = col * CELL_WIDTH
            painter.drawLine(x, 0, x, SCREEN_HEIGHT)
        # Draw horizontal grid lines
        for row in range(NUM_ROWS + 1):
            y = row * CELL_HEIGHT
            painter.drawLine(0, y, SCREEN_WIDTH, y)
        
        # Set the pen for text drawing using the configured text color
        text_color = QColor(*TEXT_COLOR)
        painter.setPen(text_color)
        
        # Draw column labels (A-Z) at the top of each column
        font = QFont("Arial", 14)
        painter.setFont(font)
        for col in range(NUM_COLUMNS):
            letter = chr(ord('A') + col)
            x = col * CELL_WIDTH
            text_rect = QRectF(x, 0, CELL_WIDTH, 30)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, letter)
        
        # Draw row labels (1-50) along the left side
        for row in range(NUM_ROWS):
            number = str(row + 1)
            y = row * CELL_HEIGHT
            text_rect = QRectF(0, y, 50, CELL_HEIGHT)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, number)

# --- Main Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Transparent Grid Overlay")
        # Set fixed geometry to fill 1920x1080 screen
        self.setGeometry(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        # Set window flags for a frameless, always-on-top, transparent window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.grid_widget = GridWidget(self)
        self.setCentralWidget(self.grid_widget)

# --- Main Application ---
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    global main_window
    main_window = window  # Save reference for command processing
    window.showFullScreen()  # Fullscreen mode; or use window.show() for windowed mode

    # Start voice recognition thread
    listener_thread = threading.Thread(target=voice_command_listener, daemon=True)
    listener_thread.start()

    # Start command processing thread
    def command_processor():
        while True:
            if not command_queue.empty():
                cmd = command_queue.get()
                process_command(cmd)
            time.sleep(0.1)
    processor_thread = threading.Thread(target=command_processor, daemon=True)
    processor_thread.start()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
