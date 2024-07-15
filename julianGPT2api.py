import sys
import requests
import json
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QLabel
from PyQt5.QtCore import QThread, pyqtSignal


class APIClient(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('API Client')

        # 创建布局
        layout = QVBoxLayout()

        # 添加显示结果的文本框
        self.textEdit = QTextEdit(self)
        layout.addWidget(self.textEdit)

        # 添加一个按钮来发送请求
        self.button = QPushButton('发送请求', self)
        self.button.clicked.connect(self.send_request)
        layout.addWidget(self.button)

        # 添加一个标签来显示状态
        self.statusLabel = QLabel('', self)
        layout.addWidget(self.statusLabel)

        # 设置窗口布局
        self.setLayout(layout)

    def send_request(self):
        # 创建并启动请求线程
        self.thread = RequestThread()
        self.thread.response_received.connect(self.update_text)
        self.thread.status_update.connect(self.update_status)
        self.thread.start()

    def update_text(self, text):
        self.textEdit.setPlainText(text)
        self.textEdit.moveCursor(self.textEdit.textCursor().End)

    def update_status(self, status):
        self.statusLabel.setText(status)


class RequestThread(QThread):
    response_received = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def run(self):
        # 设置请求参数
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6IlB1c295IiwiaWQiOjU1MTQwLCJlbWFpbCI6IjE2NDM0NjA5NTFAcXEuY29tIiwicm9sZSI6InZpZXdlciIsIm9wZW5JZCI6Im85Qk5TNlpxOFVEZExGa3ZMSlVmUWl6Y08ycm8iLCJjbGllbnQiOm51bGwsImlhdCI6MTcyMDc0NzI2MiwiZXhwIjoxNzIzMzM5MjYyfQ.Ub1KmzifFQ8v1wRRHYMITcTdxhMumMr2XB0ki4dIWQU"
        prompt = "今天多少号？"
        group_id = 327666
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        payload = {
            "prompt": prompt,
            "appId": None,
            "options": {
                "temperature": 0.8,
                "model": 3,
                "groupId": group_id,
                "usingNetwork": False
            },
            "systemMessage": ""
        }

        try:
            # 发送 POST 请求并处理响应
            with requests.post("https://chat.julianwl.com/api/chatgpt/chat-process", headers=headers, json=payload,
                               stream=True) as response:
                response.raise_for_status()

                # 获取响应流
                for line in response.iter_lines(decode_unicode=True):
                    if line:
                        # 将行解析为 JSON 对象
                        decoded_line = json.loads(line)
                        self.response_received.emit(decoded_line["text"])

                self.status_update.emit('请求成功')
        except Exception as e:
            self.response_received.emit(str(e))
            self.status_update.emit('请求失败')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    client = APIClient()
    client.show()
    sys.exit(app.exec_())
