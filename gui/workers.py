"""异步任务 Worker 模块"""

import io
from contextlib import redirect_stdout
from PySide6.QtCore import QThread, Signal


class _StreamLogEmitter(io.TextIOBase):
    """stdout 重定向流：把输出按行实时通过 Qt 信号转发到 GUI

    替代原先"任务结束后一次性 emit"的做法，抓取过程中逐行刷新界面，
    避免长时间无输出让用户误以为卡死。
    """

    def __init__(self, emit):
        super().__init__()
        self._emit = emit
        self._buf = ""

    def writable(self) -> bool:
        return True

    def write(self, text: str) -> int:
        if not text:
            return 0
        self._buf += text
        # 遇到换行就 emit 一整行，保证界面逐行滚动
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line.strip():
                self._emit(line)
        return len(text)

    def flush(self):
        if self._buf.strip():
            self._emit(self._buf)
            self._buf = ""


class ScraperWorker(QThread):
    """抓取/提取任务后台线程"""
    log_message = Signal(str)
    finished_ok = Signal(bool, str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._interrupted = False

    def request_interruption(self):
        """请求中断任务"""
        self._interrupted = True
        super().requestInterruption()

    def is_interrupted(self) -> bool:
        return self._interrupted

    def run(self):
        # 用自定义流替代 StringIO，print 输出逐行实时 emit 到 GUI
        stream = _StreamLogEmitter(self.log_message.emit)
        try:
            with redirect_stdout(stream):
                self.func(*self.args, **self.kwargs)
            stream.flush()

            if self._interrupted:
                self.finished_ok.emit(False, "用户中断")
            else:
                self.finished_ok.emit(True, "任务完成")
        except Exception as e:
            self.log_message.emit(f"[ERROR] {e}")
            self.finished_ok.emit(False, str(e))
