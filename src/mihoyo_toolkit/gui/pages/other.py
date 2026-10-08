"""其他抓取页面：角色图鉴 / 教程 / 自定义页面 / 3D 模型下载。"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from ...core import get_path_manager
from .base import BasePage

#: 教程语言下拉项：(显示文本, 传给 core 的值)
_TUTORIAL_LANGUAGES: tuple[tuple[str, str], ...] = (
    ("默认（无语言参数）", ""),
    ("中文 (zh-cn)", "zh-cn"),
    ("英文 (en-us)", "en-us"),
)


class OtherPage(BasePage):
    """图鉴、教程、自定义抓取与模型下载。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    # ------------------------------------------------------------------ #
    #  界面
    # ------------------------------------------------------------------ #
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(
            self.make_header("其他抓取", "角色图鉴、教程页面、图片提取、自定义抓取与 3D 模型下载")
        )

        self.btn_baike = self.make_button("抓取图鉴", self._run_baike)
        self.btn_extract_images = self.make_button("提取图片", self._run_extract_images)
        baike_row = QHBoxLayout()
        baike_row.setSpacing(8)
        baike_row.addWidget(self.btn_baike)
        baike_row.addWidget(self.btn_extract_images)
        baike_row.addStretch()
        layout.addLayout(baike_row)

        layout.addLayout(self._build_tutorial_form())
        layout.addLayout(self._build_custom_form())
        layout.addLayout(self._build_model_row())

        layout.addLayout(self.make_stop_row())
        layout.addWidget(self.progress)
        layout.addStretch()

        self.register_buttons(
            self.btn_baike,
            self.btn_extract_images,
            self.btn_tutorial_fetch,
            self.btn_tutorial_batch,
            self.btn_tutorial_extract,
            self.btn_custom,
            self.btn_model_download,
        )

    def _build_tutorial_form(self) -> QFormLayout:
        form = QFormLayout()
        form.setSpacing(8)

        self.tutorial_input = QLineEdit("mh4imrrhzdzi")
        self.tutorial_input.setPlaceholderText("教程 ID，例如 mh4imrrhzdzi")
        form.addRow("教程 ID：", self.tutorial_input)

        self.tutorial_lang = QComboBox()
        for label, value in _TUTORIAL_LANGUAGES:
            self.tutorial_lang.addItem(label, value)
        form.addRow("语言：", self.tutorial_lang)

        self.btn_tutorial_fetch = self.make_button("抓取教程", self._run_tutorial)
        self.btn_tutorial_batch = self.make_button("批量抓取目录", self._run_tutorial_batch)
        self.btn_tutorial_extract = self.make_button("提取数据", self._run_tutorial_extract)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        for button in (
            self.btn_tutorial_fetch,
            self.btn_tutorial_batch,
            self.btn_tutorial_extract,
        ):
            buttons.addWidget(button)
        buttons.addStretch()
        form.addRow("", buttons)
        return form

    def _build_custom_form(self) -> QFormLayout:
        form = QFormLayout()
        form.setSpacing(8)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        form.addRow("自定义 URL：", self.url_input)

        self.filename_input = QLineEdit("custom_page.html")
        self.filename_input.setPlaceholderText("custom_page.html")
        form.addRow("输出文件名：", self.filename_input)

        self.btn_custom = self.make_button("自定义抓取", self._run_custom)
        form.addRow("", self.btn_custom)
        return form

    def _build_model_row(self) -> QFormLayout:
        form = QFormLayout()
        form.setSpacing(8)

        models_dir = get_path_manager().relative(get_path_manager().models)
        self.btn_model_download = self.make_button("下载模型", self._run_model_download)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(self.btn_model_download)
        buttons.addStretch()
        form.addRow(f"3D 模型（输出目录：{models_dir}）", buttons)
        return form

    # ------------------------------------------------------------------ #
    #  动作
    # ------------------------------------------------------------------ #
    def _run_baike(self) -> None:
        from ...scrapers import run_baike

        self.run_task(run_baike, "抓取角色图鉴")

    def _run_extract_images(self) -> None:
        from ...extractors import run_extract_images

        self.run_task(run_extract_images, "提取图鉴图片链接")

    def _tutorial_args(self) -> tuple[str, str | None] | None:
        tutorial_id = self.tutorial_input.text().strip() or "mh4imrrhzdzi"
        lang = self.tutorial_lang.currentData() or None
        if not tutorial_id:
            self.log_message.emit("[WARN] 请填写教程 ID")
            return None
        return tutorial_id, lang

    def _run_tutorial(self) -> None:
        from ...scrapers import run_tutorial

        args = self._tutorial_args()
        if args is None:
            return
        tutorial_id, lang = args
        self.run_task(
            lambda: run_tutorial(tutorial_id, lang),
            f"抓取教程 {tutorial_id}",
        )

    def _run_tutorial_batch(self) -> None:
        from ...scrapers import run_tutorial_batch

        index_id = self.tutorial_input.text().strip() or "mhs2w008wf14"
        lang = self.tutorial_lang.currentData() or None
        self.run_task(
            lambda: run_tutorial_batch(index_id, lang),
            f"批量抓取教程目录 {index_id}",
        )

    def _run_tutorial_extract(self) -> None:
        from ...extractors import run_extract_tutorial

        args = self._tutorial_args()
        if args is None:
            return
        tutorial_id, lang = args
        self.run_task(
            lambda: run_extract_tutorial(tutorial_id, lang),
            f"提取教程数据 {tutorial_id}",
        )

    def _run_custom(self) -> None:
        from ...scrapers import run_custom

        url = self.url_input.text().strip()
        if not url:
            self.log_message.emit("[WARN] 请填写自定义 URL")
            return
        filename = self.filename_input.text().strip() or "custom_page.html"
        self.run_task(lambda: run_custom(url, filename), f"抓取自定义页面 {url}")

    def _run_model_download(self) -> None:
        from ...scrapers import run_model_download

        self.run_task(run_model_download, "下载 3D 模型")

    # ------------------------------------------------------------------ #
    #  结果
    # ------------------------------------------------------------------ #
    def _on_task_finished(self, result: object) -> None:
        self._restore_controls()
        if isinstance(result, int):
            self.progress.finish(f"任务完成，新增 {result} 条")
        else:
            self.progress.finish("任务完成")


__all__ = ["OtherPage"]
