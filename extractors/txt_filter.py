"""
TXT 文件过滤工具
按关键词匹配提取行，按时间降序重新编号（时间越新序号越小）

支持格式：
- 7字段：序号-标题-[日期]-[分类]-[摘要]-[封面图URL]-(完整URL)
- 4字段：序号-标题-[日期]-(URL)
- 3字段：序号-编号-名称（无日期，保持原顺序）
- 2字段：序号-标题-[URL]（无日期，保持原顺序）

匹配字段可选：整行 / 标题 / 标题+摘要 / 标题+摘要+分类
匹配方式：包含匹配，多关键词空格分隔，OR 逻辑（任一满足即命中）
"""

import os
import re
from typing import List, Tuple, Optional, Dict

from core.config_manager import config_manager
from utils.error_handler import handle_errors
from utils.logger import setup_logger, log_function_call

logger = setup_logger("TxtFilter")


# 匹配字段选项常量
FIELD_ALL = "all"                         # 整行
FIELD_TITLE = "title"                     # 仅标题
FIELD_TITLE_INTRO = "title_intro"         # 标题+摘要
FIELD_TITLE_INTRO_CAT = "title_intro_cat" # 标题+摘要+分类

FIELD_CHOICES = [
    (FIELD_ALL,              "整行（最宽松）"),
    (FIELD_TITLE,            "仅标题"),
    (FIELD_TITLE_INTRO,      "标题+摘要"),
    (FIELD_TITLE_INTRO_CAT,  "标题+摘要+分类"),
]

# 匹配模式选项常量
MATCH_EXACT = "exact"   # 精准匹配：关键词作为完整子串出现
MATCH_FUZZY = "fuzzy"   # 模糊匹配：关键词拆为 2-gram 片段，任一片段命中即匹配

MATCH_CHOICES = [
    (MATCH_EXACT, "精准匹配（完整子串）"),
    (MATCH_FUZZY, "模糊匹配（2-gram 片段）"),
]


class TxtFilter:
    """TXT 文件过滤器"""

    # 7字段：序号-标题-[日期]-[分类]-[摘要]-[封面图URL]-(完整URL)
    PATTERN_7 = re.compile(
        r'^(\d{4})-(.+?)-\[(.+?)\]-\[(.*?)\]-\[(.*?)\]-\[(.*?)\]-\((https?://.+?)\)'
    )
    # 4字段：序号-标题-[日期]-(URL)
    PATTERN_4 = re.compile(
        r'^(\d{4})-(.+?)-\[(.+?)\]-\((https?://.+?)\)'
    )
    # 3字段（characters）：序号-编号-名称
    PATTERN_3 = re.compile(r'^(\d{4})-(\d+)-(.+)')
    # 2字段（image_urls）：序号-标题-[URL]
    PATTERN_2 = re.compile(r'^(\d{4})-(.+?)-\[(https?://.+?)\]')

    def __init__(self):
        self.base_dir = config_manager.base_dir
        # 输出目录：data/results/filtered/
        self.output_dir = os.path.join(
            config_manager.get_output_dir("data"), "filtered"
        )

    # ---- 文件发现 ----

    def list_txt_files(self) -> List[Tuple[str, str, int]]:
        """扫描 data/results/ 和 data/images/ 下所有 .txt 文件

        Returns:
            [(相对路径, 绝对路径, 行数), ...] 按相对路径排序
        """
        results: List[Tuple[str, str, int]] = []

        # data/results/ 下的 txt
        data_dir = config_manager.get_output_dir("data")
        self._scan_txt(data_dir, results)

        # data/images/ 下的 txt
        images_dir = os.path.join(self.base_dir, "data", "images")
        if os.path.isdir(images_dir):
            self._scan_txt(images_dir, results)

        # 去重（按绝对路径）
        seen = set()
        unique = []
        for rel, ab, n in results:
            if ab not in seen:
                seen.add(ab)
                unique.append((rel, ab, n))

        unique.sort(key=lambda x: x[0])
        return unique

    def _scan_txt(self, root: str, results: list):
        """递归扫描 root 下的 .txt 文件"""
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                if f.endswith(".txt"):
                    abs_path = os.path.join(dirpath, f)
                    rel_path = os.path.relpath(abs_path, self.base_dir)
                    try:
                        with open(abs_path, "r", encoding="utf-8") as fh:
                            n = sum(1 for line in fh if line.strip())
                    except Exception:
                        n = -1
                    results.append((rel_path, abs_path, n))

    # ---- 行解析 ----

    def parse_line(self, line: str) -> Optional[Dict]:
        """解析一行 txt，返回结构化字典

        兼容 7/4/3/2 字段格式。无法解析的行返回 None。

        Returns:
            {index, title, date, category, intro, poster_url, url, raw, has_date}
        """
        line = line.rstrip("\n\r")
        if not line.strip():
            return None

        # 7字段
        m = self.PATTERN_7.match(line)
        if m:
            return {
                "index": m.group(1),
                "title": m.group(2),
                "date": m.group(3),
                "category": m.group(4),
                "intro": m.group(5),
                "poster_url": m.group(6),
                "url": m.group(7),
                "raw": line,
                "has_date": True,
            }

        # 4字段
        m = self.PATTERN_4.match(line)
        if m:
            return {
                "index": m.group(1),
                "title": m.group(2),
                "date": m.group(3),
                "category": "",
                "intro": "",
                "poster_url": "",
                "url": m.group(4),
                "raw": line,
                "has_date": True,
            }

        # 3字段（characters: 序号-编号-名称）
        m = self.PATTERN_3.match(line)
        if m:
            return {
                "index": m.group(1),
                "title": m.group(3),
                "date": "",
                "category": "",
                "intro": "",
                "poster_url": "",
                "url": "",
                "raw": line,
                "has_date": False,
            }

        # 2字段（image_urls: 序号-标题-[URL]）
        m = self.PATTERN_2.match(line)
        if m:
            return {
                "index": m.group(1),
                "title": m.group(2),
                "date": "",
                "category": "",
                "intro": "",
                "poster_url": m.group(3),
                "url": "",
                "raw": line,
                "has_date": False,
            }

        # 无法识别的行（非空），保留原样
        return {
            "index": "0000",
            "title": "",
            "date": "",
            "category": "",
            "intro": "",
            "poster_url": "",
            "url": "",
            "raw": line,
            "has_date": False,
        }

    # ---- 匹配逻辑 ----

    def extract_match_text(self, parsed: Dict, field_choice: str) -> str:
        """根据 field_choice 提取待匹配文本"""
        if field_choice == FIELD_ALL:
            return parsed["raw"]

        parts = []
        # title 始终包含（除非是 FIELD_ALL，已返回）
        parts.append(parsed.get("title", ""))

        if field_choice in (FIELD_TITLE_INTRO, FIELD_TITLE_INTRO_CAT):
            parts.append(parsed.get("intro", ""))

        if field_choice == FIELD_TITLE_INTRO_CAT:
            parts.append(parsed.get("category", ""))

        return " ".join(p for p in parts if p)

    @staticmethod
    def _fuzzy_substrings(keyword: str, n: int = 2) -> List[str]:
        """将关键词拆为连续 n-gram 片段列表

        例如 "千星奇域" (n=2) → ["千星", "星奇", "奇域"]
        长度不足 n 时返回原词本身。
        """
        if len(keyword) <= n:
            return [keyword]
        return [keyword[i:i + n] for i in range(len(keyword) - n + 1)]

    @staticmethod
    def match_keywords(
        text: str,
        keywords: List[str],
        match_mode: str = MATCH_EXACT,
    ) -> bool:
        """OR 逻辑：任意关键词命中 text 即返回 True（不区分大小写）

        Args:
            text: 待匹配文本
            keywords: 关键词列表
            match_mode: MATCH_EXACT（精准，完整子串）或 MATCH_FUZZY（模糊，2-gram 片段）
        """
        text_lower = text.lower()
        for kw in keywords:
            kw_lower = kw.lower()
            if match_mode == MATCH_FUZZY:
                # 模糊：关键词的任一 2-gram 片段出现在 text 中即命中
                substrings = TxtFilter._fuzzy_substrings(kw_lower)
                if any(sub in text_lower for sub in substrings):
                    return True
            else:
                # 精准：关键词作为完整子串出现
                if kw_lower in text_lower:
                    return True
        return False

    # ---- 过滤 + 排序 + 重编号 ----

    def filter_and_sort(
        self,
        file_paths: List[str],
        keywords: List[str],
        field_choice: str = FIELD_ALL,
        match_mode: str = MATCH_EXACT,
    ) -> Tuple[List[Dict], bool]:
        """读取文件 → 过滤 → 按日期降序排序 → 重新编号

        Args:
            match_mode: MATCH_EXACT 或 MATCH_FUZZY

        Returns:
            (items, has_nodate_file)
            items: 过滤排序后的字典列表
            has_nodate_file: 是否有无日期字段的文件（用于提示）
        """
        all_items: List[Dict] = []
        has_nodate_file = False

        for path in file_paths:
            if not os.path.exists(path):
                print(f"[WARN] 文件不存在: {path}")
                continue

            try:
                file_rel = os.path.relpath(path, self.base_dir)
            except (ValueError, OSError):
                file_rel = path  # 跨盘符等异常情况直接用绝对路径
            file_has_date = False
            file_nodate = False
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    parsed = self.parse_line(line)
                    if parsed is None:
                        continue

                    if parsed["has_date"]:
                        file_has_date = True
                    else:
                        file_nodate = True

                    match_text = self.extract_match_text(parsed, field_choice)
                    if self.match_keywords(match_text, keywords, match_mode):
                        # 记录来源文件和命中的关键词（供预览展示）
                        parsed["source_file"] = file_rel
                        text_lower = match_text.lower()
                        if match_mode == MATCH_FUZZY:
                            # 模糊模式：记录命中的 2-gram 片段
                            matched = []
                            for kw in keywords:
                                for sub in self._fuzzy_substrings(kw.lower()):
                                    if sub in text_lower and sub not in matched:
                                        matched.append(sub)
                            parsed["matched_keywords"] = matched
                        else:
                            parsed["matched_keywords"] = [
                                kw for kw in keywords if kw.lower() in text_lower
                            ]
                        # 保存原始序号（重编号前的）
                        parsed["old_index"] = parsed["index"]
                        all_items.append(parsed)

            if file_nodate and not file_has_date:
                has_nodate_file = True

        if not all_items:
            return [], has_nodate_file

        # 按日期降序排序（时间越新序号越小）
        # 有日期的行按日期降序，无日期的行排到最后保持原顺序
        dated = [x for x in all_items if x["has_date"]]
        nodate = [x for x in all_items if not x["has_date"]]

        if dated:
            dated.sort(key=lambda x: x["date"], reverse=True)

        sorted_items = dated + nodate

        # 重新编号（0001 起，4 位补零）
        for idx, item in enumerate(sorted_items, 1):
            new_idx = f"{idx:04d}"
            # old_index 已在匹配时保存
            # 替换 raw 行开头的旧序号
            item["raw"] = re.sub(
                r"^\d{4}-", f"{new_idx}-", item["raw"]
            )
            item["index"] = new_idx

        return sorted_items, has_nodate_file

    # ---- 输出 ----

    def build_output_name(
        self, file_paths: List[str], keywords: List[str]
    ) -> str:
        """生成输出文件名：<原文件名或 merged>_<关键词>.txt"""
        kw_str = "_".join(keywords)
        # 文件名安全化：替换非法字符
        kw_str = re.sub(r'[\\/:*?"<>|]', "_", kw_str)

        if len(file_paths) == 1:
            base = os.path.splitext(os.path.basename(file_paths[0]))[0]
        else:
            base = "merged"

        return f"{base}_{kw_str}.txt"

    def write_output(self, items: List[Dict], out_path: str) -> int:
        """将过滤后的行写入文件，返回写入行数"""
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            for item in items:
                f.write(item["raw"] + "\n")
        return len(items)

    # ---- 运行入口 ----

    def run(
        self,
        file_paths: List[str],
        keywords: List[str],
        field_choice: str = FIELD_ALL,
        match_mode: str = MATCH_EXACT,
    ) -> Optional[str]:
        """执行过滤并写入文件

        Args:
            file_paths: txt 文件路径列表
            keywords: 关键词列表（OR 逻辑）
            field_choice: 匹配字段选择
            match_mode: 匹配模式（精准/模糊）

        Returns:
            输出文件路径，无匹配返回 None
        """
        os.makedirs(self.output_dir, exist_ok=True)

        print(f"\n[FILTER] 过滤条件：")
        print(f"  文件数: {len(file_paths)}")
        print(f"  关键词: {keywords}（OR）")
        field_label = dict(FIELD_CHOICES).get(field_choice, field_choice)
        mode_label = dict(MATCH_CHOICES).get(match_mode, match_mode)
        print(f"  匹配字段: {field_label}")
        print(f"  匹配模式: {mode_label}")

        items, has_nodate_file = self.filter_and_sort(
            file_paths, keywords, field_choice, match_mode
        )

        if not items:
            print("[INFO] 未匹配到任何行")
            return None

        out_name = self.build_output_name(file_paths, keywords)
        out_path = os.path.join(self.output_dir, out_name)
        n = self.write_output(items, out_path)

        print(f"\n[OK] 过滤完成")
        print(f"  匹配行数: {n}")
        if has_nodate_file:
            print(f"  [提示] 部分文件无日期字段，已按原顺序排在末尾")
        print(f"  输出路径: {out_path}")

        if items:
            print(f"  最新: {items[0].get('date', '(无日期)')} - {items[0]['title'][:40]}")
            if len(items) > 1:
                print(f"  最旧: {items[-1].get('date', '(无日期)')} - {items[-1]['title'][:40]}")

        return out_path

    def preview(
        self,
        file_paths: List[str],
        keywords: List[str],
        field_choice: str = FIELD_ALL,
        match_mode: str = MATCH_EXACT,
    ) -> Tuple[List[Dict], bool]:
        """预览过滤结果（不写文件）

        与 run() 相同的过滤+排序+重编号逻辑，但不写入文件。
        GUI 预览对话框使用此方法获取结果后展示。

        Returns:
            (items, has_nodate_file) — 同 filter_and_sort
        """
        print(f"\n[PREVIEW] 过滤条件：")
        print(f"  文件数: {len(file_paths)}")
        print(f"  关键词: {keywords}（OR）")
        field_label = dict(FIELD_CHOICES).get(field_choice, field_choice)
        mode_label = dict(MATCH_CHOICES).get(match_mode, match_mode)
        print(f"  匹配字段: {field_label}")
        print(f"  匹配模式: {mode_label}")

        items, has_nodate_file = self.filter_and_sort(
            file_paths, keywords, field_choice, match_mode
        )

        if not items:
            print("[INFO] 未匹配到任何行")
            return [], has_nodate_file

        print(f"[PREVIEW] 匹配 {len(items)} 行")
        if items:
            print(f"  最新: {items[0].get('date', '(无日期)')} - {items[0]['title'][:40]}")
            if len(items) > 1:
                print(f"  最旧: {items[-1].get('date', '(无日期)')} - {items[-1]['title'][:40]}")

        return items, has_nodate_file

    def write_to_file(self, items: List[Dict], file_paths: List[str], keywords: List[str]) -> Optional[str]:
        """将已排序重编号的 items 写入输出文件（供 GUI 预览确认后调用）"""
        if not items:
            return None

        os.makedirs(self.output_dir, exist_ok=True)
        out_name = self.build_output_name(file_paths, keywords)
        out_path = os.path.join(self.output_dir, out_name)
        n = self.write_output(items, out_path)

        print(f"\n[OK] 过滤完成")
        print(f"  匹配行数: {n}")
        print(f"  输出路径: {out_path}")
        return out_path


# ---- CLI 交互入口 ----

@log_function_call
@handle_errors
def run_filter():
    """CLI 交互式过滤入口"""
    tf = TxtFilter()

    # 1. 列出可用 txt
    files = tf.list_txt_files()
    if not files:
        print("[WARN] 未找到任何 txt 文件")
        return

    print("\n[FILTER] TXT 文件过滤工具")
    print("=" * 70)
    print("可用文件：")
    for i, (rel, ab, n) in enumerate(files, 1):
        print(f"  {i:>2}. {rel}  ({n} 行)")
    print(f"  {len(files)+1:>2}. 手动输入文件路径")

    # 2. 选择文件
    print()
    raw = input("选择文件序号（多个用逗号分隔，如 1,3,5）: ").strip()
    if not raw:
        print("[ERROR] 未选择文件")
        return

    selected_paths = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(files):
                selected_paths.append(files[idx][1])
            elif idx == len(files):
                # 手动输入路径
                manual = input("  输入 txt 文件路径: ").strip().strip('"').strip("'")
                if manual:
                    if os.path.isfile(manual) and manual.endswith(".txt"):
                        selected_paths.append(os.path.abspath(manual))
                    else:
                        print(f"[WARN] 不是有效的 txt 文件: {manual}")
            else:
                print(f"[WARN] 序号 {part} 超出范围，已跳过")
        else:
            print(f"[WARN] 无效输入: {part}")

    if not selected_paths:
        print("[ERROR] 未选择有效文件")
        return

    print(f"\n[INFO] 已选择 {len(selected_paths)} 个文件")

    # 3. 检查是否有无日期的文件，给出提示
    nodate_files = []
    for ab in selected_paths:
        rel = os.path.relpath(ab, tf.base_dir)
        # 快速检查：读取前几行判断是否有日期字段
        has_date = False
        has_nodate = False
        with open(ab, "r", encoding="utf-8") as f:
            for j, line in enumerate(f):
                if j >= 5:
                    break
                parsed = tf.parse_line(line)
                if parsed:
                    if parsed["has_date"]:
                        has_date = True
                    else:
                        has_nodate = True
        if has_nodate and not has_date:
            nodate_files.append(rel)

    if nodate_files:
        print(f"\n[提示] 以下文件没有日期字段，将保持原顺序排在末尾：")
        for f in nodate_files:
            print(f"  - {f}")
        confirm = input("\n是否继续？(Y/n): ").strip().lower()
        if confirm == "n":
            print("[INFO] 已取消")
            return

    # 4. 选择匹配字段
    print("\n匹配字段：")
    for i, (key, label) in enumerate(FIELD_CHOICES, 1):
        print(f"  {i}. {label}")
    field_input = input("\n选择 [1]（默认整行）: ").strip()
    field_map = {str(i): k for i, (k, _) in enumerate(FIELD_CHOICES, 1)}
    field_choice = field_map.get(field_input, FIELD_ALL)

    # 4.5 选择匹配模式
    print("\n匹配模式：")
    for i, (key, label) in enumerate(MATCH_CHOICES, 1):
        print(f"  {i}. {label}")
    mode_input = input("\n选择 [1]（默认精准匹配）: ").strip()
    mode_map = {str(i): k for i, (k, _) in enumerate(MATCH_CHOICES, 1)}
    match_mode = mode_map.get(mode_input, MATCH_EXACT)

    # 5. 输入关键词
    kw_input = input("\n输入关键词（多个用空格分隔，OR 逻辑）: ").strip()
    if not kw_input:
        print("[ERROR] 关键词不能为空")
        return

    keywords = kw_input.split()

    # 6. 执行
    tf.run(selected_paths, keywords, field_choice, match_mode)
