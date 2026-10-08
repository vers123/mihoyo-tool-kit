"""TXT 文件过滤工具.

按关键词匹配提取行, 按时间方向排序并重新编号.

支持的匹配方式:

* 精确匹配: 关键词作为完整子串出现 (不区分大小写).
* 模糊匹配: 将关键词拆为连续 2-gram 片段, 任一片段命中即视为匹配.

排序方向: 降序 (默认, 时间越新序号越小) / 升序 (时间越旧序号越小);
无时间戳的行始终排在末尾并保持原顺序.

输出目录按源文件相对路径创建子文件夹 (保留原设计):
单文件输出到 ``filtered/<相对路径>/<文件名>_<关键词>.txt``,
多文件合并输出到 ``filtered/merged/``, 输出根为 ``results/filtered``.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, Field

from ..core.exceptions import StorageError
from ..core.paths import get_path_manager
from .logger import get_module_logger

logger = get_module_logger("txt_filter")

# 时间戳: 兼容 [YYYY-MM-DD] 与 [YYYY-MM-DD HH:MM:SS]
_TIMESTAMP_RE = re.compile(r"\[(\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}:\d{2})?)\]")

# 行首 4 位序号
_INDEX_RE = re.compile(r"^\d{4}-")

# 文件名非法字符
_ILLEGAL_RE = re.compile(r'[\\/:*?"<>|]')


class MatchResult(BaseModel):
    """单条匹配结果."""

    #: 在源文件中的行号 (1 起)
    line_no: int
    #: 从行内解析出的时间戳 (无则为空串)
    timestamp: str = ""
    #: 原始行文本
    text: str
    #: 命中的关键词
    matched_keywords: list[str] = Field(default_factory=list)
    #: 源文件 (相对项目根的路径)
    source_file: str = ""


class TxtFilter:
    """TXT 文件过滤器."""

    def __init__(self, output_root: Path | None = None) -> None:
        self.paths = get_path_manager()
        #: 自定义输出根目录; 为 None 时使用 results/filtered
        self._output_root = output_root

    @property
    def output_dir(self) -> Path:
        """过滤结果输出根目录."""
        return self._output_root or (self.paths.results / "filtered")

    # ------------------------------------------------------------------ #
    #  文件发现
    # ------------------------------------------------------------------ #
    def list_txt_files(self) -> list[tuple[str, Path, int]]:
        """扫描 ``results/`` 与 ``images/`` 下所有 .txt 文件.

        Returns:
            ``[(相对路径, 绝对路径, 行数), ...]``, 按相对路径排序.
        """
        files: list[tuple[str, Path, int]] = []
        seen: set[Path] = set()
        for root in (self.paths.results, self.paths.images):
            if not root.is_dir():
                continue
            for path in sorted(root.rglob("*.txt")):
                if not path.is_file() or path in seen:
                    continue
                seen.add(path)
                try:
                    with path.open(encoding="utf-8") as fh:
                        count = sum(1 for line in fh if line.strip())
                except OSError:
                    count = -1
                files.append((self.paths.relative(path), path, count))

        files.sort(key=lambda item: item[0])
        return files

    # ------------------------------------------------------------------ #
    #  解析与匹配
    # ------------------------------------------------------------------ #
    @staticmethod
    def parse_timestamp(line: str) -> str:
        """从行内提取时间戳, 兼容 ``[YYYY-MM-DD]`` 与 ``[YYYY-MM-DD HH:MM:SS]``."""
        match = _TIMESTAMP_RE.search(line)
        return match.group(1) if match else ""

    @staticmethod
    def _fuzzy_substrings(keyword: str, n: int = 2) -> list[str]:
        """将关键词拆为连续 n-gram 片段; 长度不足 n 时返回原词."""
        if len(keyword) <= n:
            return [keyword]
        return [keyword[i : i + n] for i in range(len(keyword) - n + 1)]

    @classmethod
    def match_keywords(
        cls, text: str, keywords: Sequence[str], *, fuzzy: bool = False
    ) -> list[str]:
        """返回命中的关键词列表 (OR 逻辑, 空列表表示未命中, 不区分大小写)."""
        text_lower = text.lower()
        matched: list[str] = []
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if fuzzy:
                hit = any(sub in text_lower for sub in cls._fuzzy_substrings(keyword_lower))
            else:
                hit = keyword_lower in text_lower
            if hit and keyword not in matched:
                matched.append(keyword)
        return matched

    # ------------------------------------------------------------------ #
    #  过滤 + 排序
    # ------------------------------------------------------------------ #
    def filter_text(
        self,
        text: str,
        keywords: Sequence[str],
        *,
        fuzzy: bool = False,
        ascending: bool = False,
        source_file: str = "",
    ) -> list[MatchResult]:
        """对文本内容执行过滤, 排序.

        Args:
            text: 待过滤的文本内容.
            keywords: 关键词列表 (OR 逻辑).
            fuzzy: True 使用 2-gram 模糊匹配, False 使用完整子串匹配.
            ascending: True 按时间升序, False (默认) 按时间降序.
            source_file: 源文件标识, 写入结果便于溯源与输出分组.

        Returns:
            排序后的匹配结果列表.
        """
        results: list[MatchResult] = []
        for line_no, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            matched = self.match_keywords(line, keywords, fuzzy=fuzzy)
            if not matched:
                continue
            results.append(
                MatchResult(
                    line_no=line_no,
                    timestamp=self.parse_timestamp(line),
                    text=line.rstrip("\r"),
                    matched_keywords=matched,
                    source_file=source_file,
                )
            )
        return self._sort_results(results, ascending=ascending)

    def filter_file(
        self,
        path: Path,
        keywords: Sequence[str],
        *,
        fuzzy: bool = False,
        ascending: bool = False,
    ) -> list[MatchResult]:
        """过滤单个 TXT 文件, 返回排序后的匹配结果.

        Args:
            path: 源文件路径.
            keywords: 关键词列表 (OR 逻辑).
            fuzzy: True 使用 2-gram 模糊匹配.
            ascending: True 按时间升序.

        Returns:
            匹配结果列表; 文件不存在时返回空列表.
        """
        path = Path(path)
        if not path.is_file():
            logger.warning("文件不存在: %s", path)
            return []
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise StorageError(f"读取文件失败: {path}", detail=str(exc)) from exc
        return self.filter_text(
            text,
            keywords,
            fuzzy=fuzzy,
            ascending=ascending,
            source_file=self.paths.relative(path),
        )

    @staticmethod
    def _sort_results(results: Sequence[MatchResult], *, ascending: bool) -> list[MatchResult]:
        """按时间戳排序; 无时间戳的行保持原顺序排在末尾."""
        dated = [item for item in results if item.timestamp]
        nodate = [item for item in results if not item.timestamp]
        dated.sort(key=lambda item: item.timestamp, reverse=not ascending)
        return dated + nodate

    # ------------------------------------------------------------------ #
    #  输出
    # ------------------------------------------------------------------ #
    def _rel_subfolder(self, source_file: str) -> Path:
        """由源文件相对路径生成输出子文件夹 (保留目录结构, 去掉 .txt)."""
        rel = Path(source_file)
        for root in (self.paths.results, self.paths.images, self.paths.data):
            try:
                sub = rel.relative_to(self.paths.relative(root))
            except ValueError:
                continue
            return sub.with_suffix("")
        return Path(rel.stem or rel.name)

    @staticmethod
    def _collect_keywords(items: Sequence[MatchResult]) -> list[str]:
        """汇总结果中出现过的关键词 (保持首次出现顺序)."""
        collected: list[str] = []
        for item in items:
            for keyword in item.matched_keywords:
                if keyword not in collected:
                    collected.append(keyword)
        return collected

    def export(self, results: Sequence[MatchResult], dest: Path) -> Path:
        """将匹配结果写入文件.

        Args:
            results: 匹配结果列表 (按期望顺序; 输出时按该顺序重新编号).
            dest: 输出根目录.

        Returns:
            实际写入的文件路径.
        """
        items = list(results)
        dest = Path(dest)
        sources = {item.source_file for item in items if item.source_file}

        if len(sources) == 1:
            source = next(iter(sources))
            subfolder = self._rel_subfolder(source)
            base = Path(source).stem
        else:
            subfolder = Path("merged")
            base = "merged"

        joined = "_".join(self._collect_keywords(items))
        kw_str = _ILLEGAL_RE.sub("_", joined) or "matched"
        out_path = dest / subfolder / f"{base}_{kw_str}.txt"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with out_path.open("w", encoding="utf-8") as fh:
                for index, item in enumerate(items, 1):
                    fh.write(_INDEX_RE.sub(f"{index:04d}-", item.text) + "\n")
        except OSError as exc:
            raise StorageError(f"写入过滤结果失败: {out_path}", detail=str(exc)) from exc

        logger.info("已导出 %d 行 -> %s", len(items), out_path)
        return out_path


def run_filter() -> None:
    """CLI 交互式过滤入口."""
    txt_filter = TxtFilter()

    files = txt_filter.list_txt_files()
    if not files:
        print("[WARN] 未找到任何 txt 文件")
        return

    print("\n[FILTER] TXT 文件过滤工具")
    print("=" * 70)
    print("可用文件:")
    for i, (rel, _path, count) in enumerate(files, 1):
        print(f"  {i:>2}. {rel}  ({count} 行)")
    print(f"  {len(files) + 1:>2}. 手动输入文件路径")

    raw = input("\n选择文件序号 (多个用逗号分隔, 如 1,3,5): ").strip()
    if not raw:
        print("[ERROR] 未选择文件")
        return

    selected: list[Path] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if not part.isdigit():
            print(f"[WARN] 无效输入: {part}")
            continue
        idx = int(part) - 1
        if 0 <= idx < len(files):
            selected.append(files[idx][1])
        elif idx == len(files):
            manual = input("  输入 txt 文件路径: ").strip().strip('"').strip("'")
            manual_path = Path(manual)
            if manual and manual_path.is_file() and manual_path.suffix.lower() == ".txt":
                selected.append(manual_path.resolve())
            else:
                print(f"[WARN] 不是有效的 txt 文件: {manual}")
        else:
            print(f"[WARN] 序号 {part} 超出范围, 已跳过")

    if not selected:
        print("[ERROR] 未选择有效文件")
        return

    fuzzy = input("\n使用模糊匹配(2-gram)? (y/N): ").strip().lower() == "y"
    ascending = input("按时间升序 (最早在前)? (y/N): ").strip().lower() == "y"
    kw_input = input("\n输入关键词 (多个用空格分隔, OR 逻辑): ").strip()
    if not kw_input:
        print("[ERROR] 关键词不能为空")
        return
    keywords = kw_input.split()

    results: list[MatchResult] = []
    for path in selected:
        results.extend(txt_filter.filter_file(path, keywords, fuzzy=fuzzy, ascending=ascending))
    results = txt_filter._sort_results(results, ascending=ascending)

    if not results:
        print("[INFO] 未匹配到任何行")
        return

    out_path = txt_filter.export(results, txt_filter.output_dir)
    print("\n[OK] 过滤完成")
    print(f"  匹配行数: {len(results)}")
    print(f"  输出路径: {out_path}")


__all__ = ["MatchResult", "TxtFilter", "run_filter"]
