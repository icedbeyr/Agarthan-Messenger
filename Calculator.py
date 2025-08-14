import sys
import json
from pathlib import Path
from PyQt6 import QtCore, QtWidgets, QtGui
try:
    from google import genai
except ImportError:
    import google.genai as genai

APP_NAME = "GeminiMini"
CONFIG_PATH = Path.home() / ".gemini_gui_config.json"
DEFAULT_MODEL = "gemini-1.5-flash"

class AskThread(QtCore.QThread):
    result = QtCore.pyqtSignal(str)
    def __init__(self, client: "genai.Client", model: str, contents: str):
        super().__init__()
        self.client = client
        self.model = model
        self.contents = contents
    def run(self):
        try:
            resp = self.client.models.generate_content(model=self.model, contents=self.contents)
            text = getattr(resp, "text", None) or ""
            self.result.emit(text)
        except Exception as e:
            self.result.emit(f"Error: {e}")

class GeminiApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName(APP_NAME)
        self.setWindowFlag(QtCore.Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.api_key = ""
        self.prefix = ""
        self.client = None
        self.ask_thread = None
        self._chat_showing_prompt = True
        self._load_config()
        self._build_ui()
        self._wire_screen_changes()
        if not self.api_key:
            self.stack.setCurrentWidget(self.key_page)
        elif not self.prefix:
            self.stack.setCurrentWidget(self.prefix_page)
        else:
            self._go_prompt_page()
        self._apply_current_size()

    def _load_config(self):
        if CONFIG_PATH.exists():
            try:
                cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                self.api_key = cfg.get("api_key", "")
                self.prefix = cfg.get("prefix", "")
            except Exception:
                self.api_key = ""
                self.prefix = ""
        else:
            self.api_key = ""
            self.prefix = ""
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)

    def _save_config(self):
        data = {"api_key": self.api_key, "prefix": self.prefix}
        try:
            CONFIG_PATH.write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            pass

    def _build_ui(self):
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        left_col = QtWidgets.QVBoxLayout()
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(6)
        btn_min = QtWidgets.QToolButton()
        btn_min.setText("–")
        btn_min.setFixedSize(20, 20)
        btn_min.clicked.connect(self.showMinimized)
        btn_close = QtWidgets.QToolButton()
        btn_close.setText("×")
        btn_close.setFixedSize(20, 20)
        btn_close.clicked.connect(self.close)
        left_col.addWidget(btn_min, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        left_col.addWidget(btn_close, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        left_col.addStretch(1)
        card = QtWidgets.QFrame()
        card.setFrameShape(QtWidgets.QFrame.Shape.Box)
        card.setStyleSheet(
            "QFrame { background: white; border: 1px solid #ccc; border-radius: 8px; }"
            "QLineEdit { padding: 6px; }"
            "QLabel#answer { color: #111; font-size: 11px; }"
            "QPushButton { padding: 6px 10px; }"
        )
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(8)
        self.stack = QtWidgets.QStackedWidget()
        card_layout.addWidget(self.stack)
        self.key_page = QtWidgets.QWidget()
        k = QtWidgets.QVBoxLayout(self.key_page)
        k.setSpacing(6)
        self.key_input = QtWidgets.QLineEdit()
        self.key_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("Enter Gemini API key and press Enter")
        self.key_input.returnPressed.connect(self._confirm_key)
        k.addWidget(self.key_input)
        self.stack.addWidget(self.key_page)
        self.prefix_page = QtWidgets.QWidget()
        p = QtWidgets.QVBoxLayout(self.prefix_page)
        p.setSpacing(6)
        self.prefix_input = QtWidgets.QLineEdit()
        self.prefix_input.setPlaceholderText("Enter prefix and press Enter")
        self.prefix_input.returnPressed.connect(self._confirm_prefix)
        p.addWidget(self.prefix_input)
        self.stack.addWidget(self.prefix_page)
        self.chat_page = QtWidgets.QWidget()
        c = QtWidgets.QVBoxLayout(self.chat_page)
        c.setSpacing(8)
        self.prompt_input = QtWidgets.QLineEdit()
        self.prompt_input.setPlaceholderText("Type your prompt and press Enter…")
        self.prompt_input.returnPressed.connect(self._send_prompt)
        self.answer_label = QtWidgets.QLabel(objectName="answer")
        self.answer_label.setWordWrap(True)
        self.answer_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.response_scroll = QtWidgets.QScrollArea()
        self.response_scroll.setWidgetResizable(True)
        self.response_scroll.setFixedHeight(50)
        self.response_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self._response_container = QtWidgets.QWidget()
        resp_layout = QtWidgets.QVBoxLayout(self._response_container)
        resp_layout.setContentsMargins(0, 0, 0, 0)
        resp_layout.setSpacing(0)
        resp_layout.addWidget(self.answer_label)
        self.response_scroll.setWidget(self._response_container)
        btn_row = QtWidgets.QHBoxLayout()
        self.new_prompt_btn = QtWidgets.QPushButton("New prompt")
        self.new_prompt_btn.clicked.connect(self._go_prompt_page)
        self.change_prefix_btn = QtWidgets.QPushButton("Change prefix")
        self.change_prefix_btn.clicked.connect(self._go_prefix_page)
        self.new_prompt_btn.setFixedSize(90, 25)
        self.change_prefix_btn.setFixedSize(90, 25)
        font1 = self.new_prompt_btn.font()
        font1.setPointSize(8)
        self.new_prompt_btn.setFont(font1)
        font2 = self.change_prefix_btn.font()
        font2.setPointSize(8)
        self.change_prefix_btn.setFont(font2)
        btn_row.addStretch(1)
        btn_row.addWidget(self.new_prompt_btn)
        btn_row.addWidget(self.change_prefix_btn)
        c.addWidget(self.prompt_input)
        c.addWidget(self.response_scroll)
        c.addLayout(btn_row)
        self.stack.addWidget(self.chat_page)
        root.addLayout(left_col, stretch=0)
        root.addWidget(card, stretch=1)
        if self.api_key:
            self.key_input.setText("••••••••••")
        if self.prefix:
            self.prefix_input.setText(self.prefix)
        self._set_prompt_only_ui()

    def _set_prompt_only_ui(self):
        self._chat_showing_prompt = True
        self.prompt_input.setVisible(True)
        self.response_scroll.setVisible(False)
        self.new_prompt_btn.setVisible(False)
        self.change_prefix_btn.setVisible(False)
        self._apply_current_size()

    def _set_answer_only_ui(self):
        self._chat_showing_prompt = False
        self.prompt_input.setVisible(False)
        self.response_scroll.setVisible(True)
        self.new_prompt_btn.setVisible(True)
        self.change_prefix_btn.setVisible(True)
        self._apply_current_size()

    def _go_prompt_page(self):
        self.stack.setCurrentWidget(self.chat_page)
        self._set_prompt_only_ui()
        self.prompt_input.setFocus()

    def _go_prefix_page(self):
        self.stack.setCurrentWidget(self.prefix_page)
        self.prefix_input.setFocus()
        self._apply_current_size()

    def _apply_current_size(self):
        current = self.stack.currentWidget()
        if current is self.chat_page:
            if self._chat_showing_prompt:
                target_w, target_h = 320, 100
            else:
                target_w, target_h = 320, 135
        else:
            target_w, target_h = 320, 100
        def apply_sizes():
            self.setMinimumSize(target_w, target_h)
            self.setMaximumSize(target_w, target_h)
            self._position_bottom_right()
        QtCore.QTimer.singleShot(0, apply_sizes)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        QtCore.QTimer.singleShot(0, self._position_bottom_right)

    def _wire_screen_changes(self):
        screen = QtWidgets.QApplication.primaryScreen()
        try:
            screen.availableGeometryChanged.connect(self._position_bottom_right)
        except Exception:
            pass
        try:
            screen.geometryChanged.connect(self._position_bottom_right)
        except Exception:
            pass

    def _position_bottom_right(self, *args):
        screen = QtWidgets.QApplication.primaryScreen()
        if not screen:
            return
        work = screen.availableGeometry()
        frame = self.frameGeometry()
        x = work.right() - frame.width() - 10
        y = work.bottom() - frame.height() - 10
        self.move(max(work.left(), x), max(work.top(), y))

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        e.ignore()

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        e.ignore()

    def _confirm_key(self):
        key = self.key_input.text().strip()
        if not key or key.startswith("•"):
            return
        try:
            self.client = genai.Client(api_key=key)
            self.api_key = key
            self._save_config()
            self.stack.setCurrentWidget(self.prefix_page)
            self.prefix_input.setFocus()
            self._apply_current_size()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "API Key Error", str(e))

    def _confirm_prefix(self):
        p = self.prefix_input.text().strip()
        self.prefix = p
        self._save_config()
        self._go_prompt_page()

    def _send_prompt(self):
        q = self.prompt_input.text().strip()
        if not q:
            return
        if not self.client:
            QtWidgets.QMessageBox.warning(self, "Missing API key", "Please enter your API key.")
            self.stack.setCurrentWidget(self.key_page)
            self.key_input.setFocus()
            self._apply_current_size()
            return
        contents = f"{self.prefix.strip()} {q}".strip()
        self.answer_label.setText("Thinking…")
        self.prompt_input.setEnabled(False)
        self.ask_thread = AskThread(self.client, DEFAULT_MODEL, contents)
        self.ask_thread.result.connect(self._on_answer)
        self.ask_thread.finished.connect(self._cleanup_thread)
        self.ask_thread.start()
        self.hide()

    def _on_answer(self, text: str):
        self.answer_label.setText(text or "(no content)")
        self._set_answer_only_ui()
        self.show()
        self.raise_()
        self.activateWindow()
        self._position_bottom_right()

    def _cleanup_thread(self):
        self.prompt_input.setEnabled(True)
        self.ask_thread = None

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)
    win = GeminiApp()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
