import sys
import os
import subprocess
import pathlib
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QMessageBox, QProgressBar, QListWidget
)
from PyQt5.QtCore import Qt

# ----------------------
# Function to find ffmpeg
# Works in both Python and PyInstaller one-file exe
# ----------------------
def get_ffmpeg_path():
    if getattr(sys, 'frozen', False):
        # PyInstaller one-file bundle
        base_path = sys._MEIPASS
    else:
        base_path = os.getcwd()

    if sys.platform == "win32":
        return os.path.join(base_path, "ffmpeg", "bin", "ffmpeg.exe")
    else:
        return os.path.join(base_path, "ffmpeg", "bin", "ffmpeg")  # Mac/Linux

ffmpeg_path = get_ffmpeg_path()

# ----------------------
# Drag & drop list area
# ----------------------
class DropArea(QWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

        self.list_widget = QListWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

        # Double-click removes file
        self.list_widget.itemDoubleClicked.connect(self.remove_item)

    def remove_item(self, item):
        row = self.list_widget.row(item)
        self.list_widget.takeItem(row)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                p = pathlib.Path(path)
                if p.is_file() and p.suffix.lower() == ".mp4":
                    self.list_widget.addItem(str(p))
                elif p.is_dir():
                    for file in p.rglob("*.mp4"):
                        self.list_widget.addItem(str(file))
            event.acceptProposedAction()
        else:
            event.ignore()

# ----------------------
# Main converter app
# ----------------------
class ConverterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MP4 → MOV Converter")
        self.setGeometry(300, 200, 550, 600)

        layout = QVBoxLayout()

        self.label = QLabel("Drag & drop MP4 files or folders below (double-click to remove):")
        self.drop_area = DropArea()

        self.output_label = QLabel("Output folder name (optional):")
        self.output_input = QLineEdit()
        self.output_input.setPlaceholderText("Leave empty to use today's date")

        self.convert_button = QPushButton("Convert to MOV")
        self.convert_button.clicked.connect(self.convert_files)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.hide()  # hide until used

        layout.addWidget(self.label)
        layout.addWidget(self.drop_area)
        layout.addWidget(self.output_label)
        layout.addWidget(self.output_input)
        layout.addWidget(self.convert_button)
        layout.addWidget(self.progress)

        self.setLayout(layout)

    def convert_files(self):
        # Determine output folder
        output_dir = self.output_input.text().strip()
        if not output_dir:
            today = datetime.now().strftime("%Y-%m-%d")
            output_dir = f"Converted_{today}"

        files = [self.drop_area.list_widget.item(i).text() for i in range(self.drop_area.list_widget.count())]
        if not files:
            QMessageBox.warning(self, "Error", "Please drag and drop at least one MP4 file or folder.")
            return

        # Ensure output directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        self.progress.setValue(0)
        self.progress.show()  # show progress bar

        total_files = len(files)
        for i, file in enumerate(files, start=1):
            base_name = os.path.splitext(os.path.basename(file))[0]
            output_file = os.path.join(output_dir, f"{base_name}.mov")

            try:
                subprocess.run([
                    ffmpeg_path,
                    "-i", file,
                    "-c:v", "copy",        # keep original video
                    "-c:a", "pcm_s24le",   # convert audio to 24-bit PCM
                    output_file,
                    "-y"
                ], check=True)
            except subprocess.CalledProcessError as e:
                QMessageBox.critical(self, "Conversion Error", f"Failed to convert {file}\n{e}")
                continue
            except FileNotFoundError:
                QMessageBox.critical(self, "FFmpeg Not Found", f"Cannot find ffmpeg at {ffmpeg_path}")
                return

            # Update progress
            self.progress.setValue(int((i / total_files) * 100))
            QApplication.processEvents()  # Keep GUI responsive

        self.progress.hide()  # hide after conversion
        QMessageBox.information(self, "Done", f"Converted {len(files)} files into '{output_dir}'")
        self.drop_area.list_widget.clear()  # clear list for next batch

# ----------------------
# Run app
# ----------------------
def main():
    app = QApplication(sys.argv)
    window = ConverterApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
