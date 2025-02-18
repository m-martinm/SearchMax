# nuitka-project: --onefile
# nuitka-project: --enable-plugin=pyside6
# nuitka-project: --output-dir=build
# nuitka-project: --output-filename=SearchMax
# nuitka-project-if: {OS} == "Windows":
#   nuitka-project: --windows-icon-from-ico=icon.png
#   nuitka-project: --windows-console-mode=disable
# nuitka-project-if: {OS} == "Linux":
#   nuitka-project:  --linux-icon=icon.png
# nuitka-project-if: {OS} == "Darwin":
#   nuitka-project:  --macos-app-icon=icon.png
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QTreeView,
    QLineEdit, QPushButton, QCheckBox,
    QToolButton, QStyledItemDelegate, QSplitter,
    QMenu, QLabel, QTableView,
    QMessageBox, QHeaderView, QFileSystemModel
)
from PySide6.QtCore import Qt, QDir, QProcess
from PySide6.QtGui import (
    QIntValidator, QFont, QStandardItemModel,
    QStandardItem, QValidator, QAction,
    QTextDocument, QIcon, QPixmap
)
import subprocess
import os
from pathlib import Path
import json
import re
import sys
import platform

if platform.system() == "Windows":
    PATH_DIVIDER = "\\"
else:
    PATH_DIVIDER = "/"


class SuffixValidator(QValidator):
    def validate(self, input_str: str, pos: int):
        pattern = r'^(\d+)([kMG]?)$'
        match = re.match(pattern, input_str.strip(), re.IGNORECASE)
        if input_str == "":
            return QValidator.Acceptable, input_str, pos
        if match:
            return QValidator.Acceptable, input_str, pos
        else:
            return QValidator.Invalid, input_str, pos


class RichTextDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        text = index.data(Qt.DisplayRole)
        if text:
            doc = QTextDocument()
            doc.setHtml(text)
            painter.save()
            painter.translate(option.rect.topLeft())
            doc.drawContents(painter)
            painter.restore()
        else:
            super().paint(painter, option, index)


class CheckableDropdown(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        self.button = QToolButton(self)
        self.button.setText("Select adapters")
        self.button.setPopupMode(QToolButton.InstantPopup)
        layout.addWidget(self.button)

        self.menu = QMenu(self)
        self.button.setMenu(self.menu)

        self.options = ["pandoc", "poppler", "postprocpagebreaks",
                        "ffmpeg", "zip", "decompress", "tar", "sqlite", "mail"]
        self.actions = []

        for option in self.options:
            action = QAction(option, self)
            action.setCheckable(True)
            action.setChecked(True)
            self.menu.addAction(action)
            self.actions.append(action)
            action.triggered.connect(self.keep_menu_open)

    def keep_menu_open(self):
        self.button.showMenu()


class SeachMax(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SearchMax")
        self.setGeometry(100, 100, 1280, 720)

        pixmap = QPixmap("icon.png")
        self.setWindowIcon(QIcon(pixmap))

        self.font: QFont = self.font()
        self.font.setPointSize(10)
        self.setFont(self.font)
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.main_splitter = QSplitter(Qt.Horizontal)

        self.current_dir: Path = Path.cwd()
        self.current_dir_label = QLabel()
        self.set_current_path_label()
        # Left Panel - Folder View
        self.left_widget_layout = QWidget()
        self.left_layout = QVBoxLayout(self.left_widget_layout)

        self.folder_view = QTreeView()
        self.folder_model = QFileSystemModel()
        self.folder_view.setModel(self.folder_model)
        self.folder_model.setRootPath("")
        self.folder_model.setResolveSymlinks(True)
        self.folder_model.setFilter(
            QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot | QDir.Filter.NoSymLinks)
        self.folder_view.setRootIndex(self.folder_model.index(""))
        self.folder_view.setExpanded(self.folder_model.index(str(self.current_dir)), True)
        # TODO: Add option to show/hide hidden folders
        self.folder_view.setColumnHidden(1, True)
        self.folder_view.setColumnHidden(2, True)
        self.folder_view.setColumnHidden(3, True)
        self.folder_view.setHeaderHidden(True)
        self.folder_view.setToolTip("Double click on a folder to start a search in it.")
        self.folder_view.doubleClicked.connect(self.folder_double_clicked)

        self.left_layout.addWidget(self.current_dir_label)
        self.left_layout.addWidget(self.folder_view)

        # Right Panel - Central Layout
        self.central_widget_layout = QWidget()
        self.central_layout = QVBoxLayout(self.central_widget_layout)

        # Top Search Bar Layout
        self.file_types_combobox = CheckableDropdown()
        self.search_layout = QHBoxLayout()
        self.search_query = QLineEdit()
        self.search_query.setPlaceholderText("Enter search query...")
        self.search_query.setMinimumHeight(30)
        tmp = self.search_query.font()
        tmp.setPointSize(11)
        self.search_query.setFont(tmp)
        self.search_button = QPushButton("Search")

        self.search_button.clicked.connect(self.start_search)
        self.search_button.setShortcut("Return")
        self.search_layout.addWidget(self.file_types_combobox)
        self.search_layout.addWidget(self.search_query)
        self.search_layout.addWidget(self.search_button)

        # Checkbox Layout
        self.options_layout = QHBoxLayout()
        self.exclude_label = QLabel("Exclude")
        self.exclude_input = QLineEdit()
        self.exclude_input.setPlaceholderText("target/**;*.h")
        self.exclude_input.setMinimumWidth(200)
        self.case_sensitive = QCheckBox("Case sensitive")
        self.invert_match = QCheckBox("Invert match")
        self.multiline = QCheckBox("Multiline")
        self.ignore_vcs = QCheckBox("Ignore .gitignore")
        self.max_count_label = QLabel("Max count")
        self.max_count = QLineEdit("0")
        self.max_count.setValidator(QIntValidator(bottom=0))
        self.max_count.setMaximumWidth(50)
        self.max_file_size = QLineEdit("50M")
        self.max_file_size_label = QLabel("Max file size")
        self.max_file_size.setValidator(SuffixValidator())
        self.max_file_size.setPlaceholderText("10k, 10M, 1G...")
        self.options_layout.addWidget(self.exclude_label)
        self.options_layout.addWidget(self.exclude_input)
        self.options_layout.addWidget(self.case_sensitive)
        self.options_layout.addWidget(self.invert_match)
        self.options_layout.addWidget(self.multiline)
        self.options_layout.addWidget(self.ignore_vcs)
        self.options_layout.addWidget(self.max_count_label)
        self.options_layout.addWidget(self.max_count)
        self.options_layout.addWidget(self.max_file_size_label)
        self.options_layout.addWidget(self.max_file_size)

        # Search results display
        self.search_results = QTableView()
        self.search_results_model = QStandardItemModel()

        self.search_results_model.setColumnCount(3)
        self.search_results_model.setHorizontalHeaderLabels(["Path", "Line", "Text"])

        self.search_results.setModel(self.search_results_model)
        self.search_results.setItemDelegate(RichTextDelegate())
        self.search_results.setEditTriggers(QTableView.NoEditTriggers)
        self.search_results.verticalHeader().setVisible(False)
        self.search_results.doubleClicked.connect(self.open_file_at_line)
        self.search_results.resizeColumnToContents(0)
        self.search_results.resizeColumnToContents(1)
        # TODO: not the most optimal solution
        self.search_results.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.search_results.setAlternatingRowColors(True)

        # Setup central layout
        self.central_layout.addLayout(self.search_layout)
        self.central_layout.addLayout(self.options_layout)
        self.central_layout.addWidget(self.search_results)

        self.main_splitter.addWidget(self.left_widget_layout)
        self.main_splitter.addWidget(self.central_widget_layout)

        self.main_splitter.setStretchFactor(0, 2)
        self.main_splitter.setStretchFactor(1, 3)

        main_layout = QVBoxLayout(self.central_widget)
        main_layout.addWidget(self.main_splitter)

        self.status_bar = self.statusBar()
        self.process: None | QProcess = None

    def closeEvent(self, event):
        if self.process is not None:
            reply = QMessageBox.question(
                self, "Confirm Close", "Are you sure you want to close the window?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.process.readyReadStandardOutput.disconnect()
                self.process.readyReadStandardError.disconnect()
                self.process.finished.disconnect()
                self.process.kill()
                self.process = None
                event.accept()
            else:
                event.ignore()
        else:
            super().closeEvent(event)

    def start_search(self):
        query = self.search_query.text().strip()
        if not query or self.process is not None:
            return

        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.hande_search_stdout)
        self.process.readyReadStandardError.connect(self.handle_search_stderr)
        self.process.finished.connect(self.handle_search_finished)
        args = [f"-g !{e.strip()}" for e in self.exclude_input.text().split(";") if e.strip()]
        allowed_adapters = [opt.text()
                            for opt in self.file_types_combobox.actions if opt.isChecked()]
        if allowed_adapters:
            args.append("--rga-adapters=+" + ",".join(allowed_adapters))
        disallowed_adapters = [opt.text()
                               for opt in self.file_types_combobox.actions if not opt.isChecked()]
        if disallowed_adapters:
            args.append("--rga-adapters=-" + ",".join(disallowed_adapters))
        if self.case_sensitive.isChecked():
            args.append("-s")
        else:
            args.append("-i")
        if self.invert_match.isChecked():
            args.append("-v")
        if self.multiline.isChecked():
            args.append("-U")
        if self.ignore_vcs.isChecked():
            args.append("--no-ignore-vcs")
        max_count = self.max_count.text().strip()
        if max_count and max_count != "0":
            args.append(f"--max-count={max_count}")
        max_file_sz = self.max_file_size.text().strip()
        if max_file_sz and max_file_sz != 0:
            args.append(f"--max-filesize={max_file_sz}")

        self.process.setWorkingDirectory(str(self.current_dir))
        self.process.start(
            "rga", ["-n", "--json", *args, "-e", query, "."],
            QProcess.OpenModeFlag.ReadOnly | QProcess.OpenModeFlag.Unbuffered
        )
        self.status_bar.clearMessage()
        self.search_results_model.clear()
        self.search_results_model.setHorizontalHeaderLabels(["Path", "Line", "Text"])

    def hande_search_stdout(self):
        if self.process is None:
            return
        stdout = self.process.readAllStandardOutput()
        stdout = bytes(stdout).decode("utf-8")
        for line in stdout.splitlines():
            try:
                obj = json.loads(line)
                data = obj.get("data", dict())
                obj_type = obj.get("type", "")
                if obj_type == "match":
                    self.add_search_result(data)
                elif obj_type == "summary":
                    stats = data.get("stats", None)
                    if stats is not None:
                        self.status_bar.showMessage(
                            f"{stats['matches']} matches found in {stats['elapsed']['human']}")
            except json.JSONDecodeError:
                continue

    def handle_search_stderr(self):  # TODO: handle error a bit better, Access denied or permission denied
        if self.process is None:
            return
        if not self.process.isOpen():
            return
        stderr = self.process.readAllStandardError()
        stderr = bytes(stderr).decode("utf-8")
        if len(stderr) > 1024:
            stderr = stderr[:1024] + "..."
        QMessageBox.critical(self, "Error", stderr)
        self.process.readyReadStandardOutput.disconnect()
        self.process.readyReadStandardError.disconnect()
        self.process.finished.disconnect()
        self.process.kill()
        self.process = None

    def handle_search_finished(self):
        if self.process is None:
            return
        self.search_results.resizeColumnToContents(0)
        self.search_results.resizeColumnToContents(1)
        self.search_results.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Stretch)  # TODO: not the most optimal solution
        match self.process.exitCode():
            case 1:
                self.status_bar.showMessage("No matches found.", 5000)
            case 2:
                self.status_bar.showMessage("An unknown error occured.", 5000)
        self.process = None

    def set_current_path_label(self):
        path = str(self.current_dir)
        max_len = 50
        if len(path) > max_len:
            self.current_dir_label.setText("..." + path[-max_len:])
        else:
            self.current_dir_label.setText(str(self.current_dir))

    def folder_double_clicked(self, index):
        self.current_dir = Path(self.folder_model.filePath(index))
        self.set_current_path_label()
        self.folder_view.setExpanded(index, True)
        self.start_search()

    def add_search_result(self, data: dict):
        if (path := data.get("path", {}).get("text", None)) is None:
            return
        full_path = self.current_dir / path
        if (line_number := data.get("line_number", None)) is None:
            return
        if (txt := data.get("lines", {}).get("text", None)) is None:
            return
        richtxt = txt
        submatches = data.get("submatches", [])
        submatches.sort(key=lambda x: x["start"])
        offset = 0
        # TODO: Maybe also check these keys, but doesnt't seem to be an issue right now
        for s in submatches:
            start = s["start"] + offset
            end = s["end"] + offset
            matched_text = s["match"]["text"]
            new_text = f'<span style="background-color: #828282; font-weight:bold;">{matched_text}</span>'
            richtxt = richtxt[:start] + new_text + richtxt[end:]

            offset += len(new_text) - (end - start)

        res = re.search(r"Page (\d+):", richtxt)
        if res is not None:
            line_number = "Page " + res.group(1)
            richtxt = re.sub(r"Page (\d+):", "", richtxt)
            txt = re.sub(r"Page (\d+):", "", txt)

        # TODO: Some problems: 1. two files can have the same "path" 2. sometimes unnecesarry to display the parent
        path_item = QStandardItem(full_path.parent.name + PATH_DIVIDER + full_path.name)
        path_item.setToolTip(str(full_path))
        path_item.setFlags(path_item.flags() & ~Qt.ItemIsEditable)
        line_item = QStandardItem(str(line_number))
        line_item.setFlags(line_item.flags() & ~Qt.ItemIsEditable)
        txt_item = QStandardItem()
        txt_item.setData(richtxt.strip(), Qt.DisplayRole)  # TODO: Add setting to strip lines
        # TODO: Ok temporary solution but would be better to have a smooth scroll
        txt_item.setToolTip(txt)
        txt_item.setFlags(txt_item.flags() & ~Qt.ItemIsEditable)
        self.search_results_model.appendRow([path_item, line_item, txt_item])

    def open_file_at_line(self, index):
        path_item = self.search_results_model.item(index.row(), 0)
        file_path = self.current_dir / Path(path_item.text())
        pname = platform.system().lower()
        try:
            if "windows" in pname:
                os.startfile(file_path)
            elif "linux" in pname:
                subprocess.run(["xdg-open", file_path], check=True)
            else:
                subprocess.run(["open", file_path], check=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file: {e}")


if __name__ == "__main__":
    app = QApplication([])
    window = SeachMax()
    window.show()
    window.setFocus()
    window.search_query.setFocus()
    sys.exit(app.exec())
