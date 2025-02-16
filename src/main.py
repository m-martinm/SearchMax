from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
    QTreeView, QLineEdit, QPushButton, QCheckBox,
    QSplitter, QMenuBar, QMenu, QLabel, QTableView, QMessageBox, QHeaderView, QFileSystemModel
)
from PySide6.QtCore import Qt, QDir
from PySide6.QtGui import QIntValidator, QFont, QStandardItemModel, QStandardItem, QValidator
import subprocess
import os
from pathlib import Path
import json
import re
import platform


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


class SeachMax(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SearchMax")
        self.setGeometry(100, 100, 1280, 720)
        self.font: QFont = self.font()
        self.font.setPointSize(10)
        self.setFont(self.font)
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.main_splitter = QSplitter(Qt.Horizontal)

        # Left Panel - Folder View
        self.folder_view = QTreeView()
        self.folder_model = QFileSystemModel()
        self.folder_model.setRootPath(str(Path.cwd()))
        self.folder_view.setModel(self.folder_model)
        # TODO: Add option to show/hide hidden folders
        self.folder_model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot)
        self.folder_view.setColumnHidden(1, True)
        self.folder_view.setColumnHidden(2, True)
        self.folder_view.setColumnHidden(3, True)
        self.main_splitter.addWidget(self.folder_view)
        self.folder_view.doubleClicked.connect(self.folder_double_clicked)

        # Right Panel - Central Layout
        self.central_widget_layout = QWidget()
        self.central_layout = QVBoxLayout(self.central_widget_layout)

        # Top Search Bar Layout
        self.search_layout = QHBoxLayout()
        self.search_query = QLineEdit()
        self.search_query.setPlaceholderText("Enter search query...")
        self.search_query.setMinimumHeight(30)
        tmp = self.search_query.font()
        tmp.setPointSize(11)
        self.search_query.setFont(tmp)
        self.search_button = QPushButton("Search")

        self.search_button.clicked.connect(self.search)  # TODO: start it seperate thread
        self.search_button.setShortcut("Return")
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
        self.max_count_label = QLabel("Max count")
        self.max_count = QLineEdit("0")
        self.max_count.setValidator(QIntValidator(bottom=0))
        self.max_count.setMaximumWidth(50)
        self.max_file_size = QLineEdit()
        self.max_file_size_label = QLabel("Max file size")
        self.max_file_size.setValidator(SuffixValidator())
        self.max_file_size.setPlaceholderText("10k, 10M, 1G...")
        self.options_layout.addWidget(self.exclude_label)
        self.options_layout.addWidget(self.exclude_input)
        self.options_layout.addWidget(self.case_sensitive)
        self.options_layout.addWidget(self.invert_match)
        self.options_layout.addWidget(self.multiline)
        self.options_layout.addWidget(self.max_count_label)
        self.options_layout.addWidget(self.max_count)
        self.options_layout.addWidget(self.max_file_size_label)
        self.options_layout.addWidget(self.max_file_size)

        self.search_results = QTableView()
        self.search_results_model = QStandardItemModel()
        self.search_results_model.setColumnCount(3)
        self.search_results_model.setHorizontalHeaderLabels(["Path", "Line", "Text"])
        self.search_results.setModel(self.search_results_model)
        self.search_results.setEditTriggers(QTableView.NoEditTriggers)
        self.search_results.verticalHeader().setVisible(False)
        self.search_results.doubleClicked.connect(self.open_file_at_line)
        self.search_results.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.search_results.setAlternatingRowColors(True)

        self.central_layout.addLayout(self.search_layout)
        self.central_layout.addLayout(self.options_layout)
        self.central_layout.addWidget(self.search_results)

        self.main_splitter.addWidget(self.central_widget_layout)

        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 2)

        main_layout = QVBoxLayout(self.central_widget)
        main_layout.addWidget(self.main_splitter)

        self.menu_bar = QMenuBar(self)
        self.menu_options = QMenu("Options", self)
        self.open_folder = self.menu_options.addAction("Open folder")
        self.open_folder.triggered.connect(self.select_folder)
        self.menu_bar.addMenu(self.menu_options)
        self.setMenuBar(self.menu_bar)
        self.status_bar = self.statusBar()
        self.setup_treeview()

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            os.chdir(folder)
            self.setup_treeview()

    def folder_double_clicked(self, index):
        cwd = Path.cwd()
        os.chdir(self.folder_model.filePath(index))
        self.search()
        os.chdir(cwd)

    def setup_treeview(self):
        self.folder_model.setRootPath(str(Path.cwd()))
        self.folder_view.setRootIndex(self.folder_model.index(str(Path.cwd())))
        self.folder_model.setResolveSymlinks(True)

    def search(self):
        query = self.search_query.text().strip()
        if not query:
            return
        excludes = [f"-g !{e.strip()}" for e in self.exclude_input.text().split(";") if e.strip()]
        args = excludes

        if self.case_sensitive.isChecked():
            args.append("-s")
        else:
            args.append("-i")

        if self.invert_match.isChecked():
            args.append("-v")

        if self.multiline.isChecked():
            args.append("-U")

        max_count = self.max_count.text().strip()
        if max_count and max_count != "0":
            args.append(f"--max-count={max_count}")

        max_file_sz = self.max_file_size.text().strip()
        if max_file_sz and max_file_sz != 0:
            args.append(f"--max-filesize={max_file_sz}")
        output = subprocess.run(
            ["rga", "-n", "--json", *args, query],
            text=True,
            encoding="utf-8",
            capture_output=True
        )
        self.status_bar.clearMessage()
        match output.returncode:
            case 1:
                self.status_bar.showMessage("No matches found.", 5000)
                return
            case 2:
                self.status_bar.showMessage(output.stderr, 5000)
                return
        self.search_results_model.clear()

        for line in output.stdout.splitlines():
            try:
                obj = json.loads(line)
                if obj.get("type") == "match":
                    self.add_search_result(obj["data"])
                    # TODO: Handle submatches properly if needed
                elif obj.get("type") == "summary":
                    stats = obj["data"]["stats"]
                    self.status_bar.showMessage(
                        f"{stats['matches']} found in {stats['elapsed']['human']}")
            except json.JSONDecodeError:
                continue

        self.search_results_model.setHorizontalHeaderLabels(["Path", "Line", "Text"])
        self.search_results.setColumnWidth(0, self.search_results.width() // 8 * 2 - 5)
        self.search_results.resizeColumnToContents(1)
        self.search_results.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

    def add_search_result(self, data):
        path = Path(data["path"]["text"])
        full_path = Path.cwd() / path
        line_number = data["line_number"]
        txt = data["lines"]["text"]
        res = re.search(r"Page (\d+):", txt)
        pdf_present = False
        if res is not None:
            line_number = res.group(1)
            txt = re.sub(r"Page (\d+):", "", txt)
            pdf_present = True

        # Add the data to the model
        path_item = QStandardItem(str(path))
        path_item.setToolTip(str(full_path))
        path_item.setFlags(path_item.flags() & ~Qt.ItemIsEditable)
        line_item = QStandardItem(str(line_number))
        line_item.setFlags(line_item.flags() & ~Qt.ItemIsEditable)
        if pdf_present:
            line_item.setToolTip("It's actually page number here :)")
        txt_item = QStandardItem(txt)
        txt_item.setFlags(txt_item.flags() & ~Qt.ItemIsEditable)
        self.search_results_model.appendRow([path_item, line_item, txt_item])

    def open_file_at_line(self, index):
        path_item = self.search_results_model.item(index.row(), 0)
        file_path = Path.cwd() / Path(path_item.text())
        try:
            if "windows" in platform.system().lower():
                os.startfile(file_path)
            else:
                subprocess.run(["xdg-open", file_path], check=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file: {e}")


if __name__ == "__main__":
    app = QApplication([])
    window = SeachMax()
    window.show()
    app.exec()
    window.setFocus()
    window.search_query.setFocus()
