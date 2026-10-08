"""utils.txt_filter 单元测试。"""

from __future__ import annotations

from pathlib import Path

from mihoyo_toolkit.core.paths import get_path_manager
from mihoyo_toolkit.utils.txt_filter import MatchResult, TxtFilter, run_filter


def test_match_result_defaults() -> None:
    result = MatchResult(line_no=1, text="hello")
    assert result.matched_keywords == []
    assert result.timestamp == ""
    assert result.source_file == ""


def test_output_dir_default_and_custom(tmp_path: Path) -> None:
    assert TxtFilter().output_dir == get_path_manager().results / "filtered"
    assert TxtFilter(tmp_path / "custom").output_dir == tmp_path / "custom"


def test_parse_timestamp() -> None:
    assert TxtFilter.parse_timestamp("[2024-01-02] 标题") == "2024-01-02"
    assert TxtFilter.parse_timestamp("[2024-01-02 03:04:05] 标题") == "2024-01-02 03:04:05"
    assert TxtFilter.parse_timestamp("没有时间戳") == ""


def test_match_keywords_exact() -> None:
    assert TxtFilter.match_keywords("Hello World", ["hello"]) == ["hello"]
    assert TxtFilter.match_keywords("abc def", ["xyz", "abc"]) == ["abc"]
    assert TxtFilter.match_keywords("abc", []) == []


def test_match_keywords_fuzzy() -> None:
    assert TxtFilter.match_keywords("这是登录页面", ["登录页面"], fuzzy=True) == ["登录页面"]
    assert TxtFilter.match_keywords("abc", ["登录"], fuzzy=True) == []


def test_filter_text_sorting() -> None:
    filt = TxtFilter()
    text = "\n".join(
        [
            "[2024-01-01] 登录问题 a",
            "",
            "[2024-01-03] 登录问题 b",
            "无时间戳 登录",
            "[2024-01-02] 登录问题 c",
        ]
    )
    results = filt.filter_text(text, ["登录"], source_file="data/results/x.txt")
    assert [r.timestamp for r in results] == [
        "2024-01-03",
        "2024-01-02",
        "2024-01-01",
        "",
    ]
    assert results[0].line_no == 3
    assert results[-1].line_no == 4

    ascending = filt.filter_text(text, ["登录"], ascending=True, source_file="s")
    assert ascending[0].timestamp == "2024-01-01"
    assert ascending[-1].timestamp == ""


def test_filter_file(tmp_path: Path) -> None:
    src = tmp_path / "a.txt"
    src.write_text("[2024-01-01] 登录\n其他\n", encoding="utf-8")
    filt = TxtFilter()

    results = filt.filter_file(src, ["登录"])
    assert len(results) == 1
    assert results[0].source_file.endswith("a.txt")
    assert filt.filter_file(tmp_path / "missing.txt", ["登录"]) == []


def test_list_txt_files() -> None:
    results_dir = get_path_manager().results
    (results_dir / "sub").mkdir(parents=True, exist_ok=True)
    (results_dir / "sub" / "a.txt").write_text("line1\nline2\n", encoding="utf-8")
    images_dir = get_path_manager().images
    (images_dir / "b.txt").write_text("x\n", encoding="utf-8")

    files = TxtFilter().list_txt_files()
    rels = [rel for rel, _, _ in files]
    assert rels == sorted(rels)
    assert len(files) == 2
    counts = {rel: count for rel, _, count in files}
    assert sum(counts.values()) == 3


def test_export_single_source(tmp_path: Path) -> None:
    filt = TxtFilter()
    results = [
        MatchResult(
            line_no=5,
            timestamp="2024-01-02",
            text="0001-old-[2024-01-02]",
            matched_keywords=["登录"],
            source_file="data/results/a.txt",
        ),
        MatchResult(
            line_no=1,
            timestamp="2024-01-03",
            text="0003-new-[2024-01-03]",
            matched_keywords=["登录"],
            source_file="data/results/a.txt",
        ),
    ]
    dest = tmp_path / "out"
    out_path = filt.export(results, dest)

    assert out_path == dest / "a" / "a_登录.txt"
    lines = out_path.read_text(encoding="utf-8").splitlines()
    # export 按给定顺序重新编号（不做排序）
    assert lines[0] == "0001-old-[2024-01-02]"
    assert lines[1] == "0002-new-[2024-01-03]"


def test_export_sanitizes_keywords(tmp_path: Path) -> None:
    filt = TxtFilter()
    results = [
        MatchResult(
            line_no=1,
            text="0001-line",
            matched_keywords=["a/b"],
            source_file="s.txt",
        )
    ]
    out_path = filt.export(results, tmp_path / "out")
    assert out_path.name == "s_a_b.txt"


def test_export_merged(tmp_path: Path) -> None:
    filt = TxtFilter()
    results = [
        MatchResult(
            line_no=1, text="0001-a", matched_keywords=["kw"], source_file="data/results/a.txt"
        ),
        MatchResult(
            line_no=2, text="0002-b", matched_keywords=["kw"], source_file="data/results/b.txt"
        ),
    ]
    out_path = filt.export(results, tmp_path / "out")
    assert out_path == tmp_path / "out" / "merged" / "merged_kw.txt"


def test_run_filter_no_files() -> None:
    run_filter()  # 未找到 txt 文件时直接返回


def test_run_filter_interactive(tmp_path: Path, monkeypatch) -> None:
    results_dir = get_path_manager().results
    (results_dir / "a.txt").write_text("[2024-01-01] 登录\n", encoding="utf-8")

    inputs = iter(["1", "n", "n", "登录"])
    monkeypatch.setattr("builtins.input", lambda *_: next(inputs))

    run_filter()

    out_path = TxtFilter().output_dir / "a" / "a_登录.txt"
    assert out_path.is_file()


def test_run_filter_empty_selection(tmp_path: Path, monkeypatch) -> None:
    results_dir = get_path_manager().results
    (results_dir / "a.txt").write_text("[2024-01-01] 登录\n", encoding="utf-8")

    inputs = iter([""])
    monkeypatch.setattr("builtins.input", lambda *_: next(inputs))
    run_filter()  # 未选择文件 → 打印错误后返回
