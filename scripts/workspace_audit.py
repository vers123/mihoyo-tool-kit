"""工作区权限 / 可写性审计（只读探测，不修改任何权限）。

用途：确认「工作区内所有目录可写可删、无异常只读文件」，并在出现真实失败时
给出可操作的下一步。**本脚本不会修改 ACL、owner 或只读属性。**

检查项：

1. 根目录 ACL：区分继承 / 显式条目，并标注 Windows 沙箱的预期条目；
2. 逐运行时目录探针：``create → write → read → delete``（写探针只在临时子目录内进行）；
3. 只读属性文件（排除 ``.git/objects`` 等 git 自身对象）；
4. 系统临时目录下的本项目残留目录；
5. 仓库内的可重建缓存目录体积。

用法::

    python scripts/workspace_audit.py            # 文本报告
    python scripts/workspace_audit.py --json     # JSON 报告（便于回归对比）
    python scripts/workspace_audit.py --home D:\\path\\to\\root

退出码：``0`` 全部通过；``1`` 存在真实失败项。
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import tempfile
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

#: 允许脚本以「仓库源码」身份运行，无需安装包
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from mihoyo_toolkit.core.paths import PathManager  # noqa: E402
from mihoyo_toolkit.core.temp import TEMP_PREFIX  # noqa: E402

#: 不参与只读属性扫描的目录（git 对象与其内部临时文件天然只读 / 无需关心）
_READONLY_SKIP = (".git", ".venv")

#: 视为可重建缓存的目录名
_CACHE_DIRS = (
    "build",
    "dist",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "htmlcov",
)

#: Windows 沙箱写入的预期 ACL 条目（出现属正常，不应修改）
_EXPECTED_DENY_RIGHTS = {"DeleteSubdirectoriesAndFiles"}


@dataclass
class ProbeResult:
    """单个目录的探针结果。"""

    path: str
    exists: bool
    create: bool
    write: bool
    read: bool
    delete: bool
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.create and self.write and self.read and self.delete


@dataclass
class AclEntry:
    """一条 ACL 记录（仅用于展示，不做任何修改）。"""

    identity: str
    rights: str
    allow: bool
    inherited: bool
    expected: bool = False


@dataclass
class AuditReport:
    """一次完整审计的结果。"""

    root: str
    temp_root: str
    acl: list[AclEntry] = field(default_factory=list)
    probes: list[ProbeResult] = field(default_factory=list)
    readonly_files: list[str] = field(default_factory=list)
    stale_temp_dirs: list[str] = field(default_factory=list)
    cache_dirs: list[dict[str, object]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def failures(self) -> list[str]:
        """真实失败项（会决定退出码）。"""
        problems: list[str] = []
        problems.extend(
            f"目录探针失败: {p.path}（{p.error or '权限不足'}）" for p in self.probes if not p.ok
        )
        problems.extend(f"只读文件: {path}" for path in self.readonly_files)
        return problems

    @property
    def ok(self) -> bool:
        return not self.failures


def _expected_ace(identity: str, rights: str, *, allow: bool) -> bool:
    """判断某条 ACE 是否需要人工关注。

    只对**拒绝**条目判定：Windows 沙箱写入的 ``Everyone: DeleteSubdirectoriesAndFiles``
    属预期，其余拒绝项需要人工确认。允许条目一律视为正常（基线 ACL 由系统盘继承而来）。
    """
    if allow:
        return True
    right_names = {part.strip() for part in rights.split(",")}
    return identity == "Everyone" and bool(right_names & _EXPECTED_DENY_RIGHTS)


def _audit_acl(root: Path) -> tuple[list[AclEntry], list[str]]:
    """读取根目录 ACL；非 Windows 或读取失败时返回空列表与说明。"""
    if os.name != "nt":
        return [], ["非 Windows 平台：跳过 ACL 审计"]

    import subprocess

    try:
        completed = subprocess.run(
            ["icacls", str(root)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - 环境相关
        return [], [f"读取 ACL 失败: {exc}"]

    entries: list[AclEntry] = []
    # icacls 首行同时带目标路径与第一条 ACE（``D:\path Everyone:(CI)(DENY)(DC)``），
    # 其余行只有 ACE。因此按 ``":("`` 定位 ACE 起点，并先去掉路径前缀，
    # 避免把盘符冒号误当成身份与权限的分隔符。
    root_prefix = f"{root} "
    for line in completed.stdout.splitlines():
        text = line.strip()
        if text.startswith(root_prefix):
            text = text[len(root_prefix) :].strip()
        marker = text.find(":(")
        if marker <= 0:
            continue
        identity = text[:marker].strip()
        flags = text[marker + 1 :].strip()
        allow = "(DENY)" not in flags
        rights = ", ".join(part for part in _split_flags(flags) if part)
        entries.append(
            AclEntry(
                identity=identity,
                rights=rights,
                allow=allow,
                inherited="(I)" in flags,
                expected=_expected_ace(identity, rights, allow=allow),
            )
        )
    notes: list[str] = []
    unexpected = [e for e in entries if not e.expected and not e.allow]
    if unexpected:
        notes.append("存在非预期的拒绝条目，请人工确认后再决定是否修复")
    return entries, notes


def _split_flags(flags: str) -> Iterable[str]:
    """把 ``(OI)(CI)(F)`` 这类标记切分成可读项。"""
    cleaned = flags.replace("(", " (").strip()
    for token in cleaned.split():
        token = token.strip()
        if not token.startswith("("):
            continue
        value = token.strip("()")
        yield {
            "OI": "ObjectInherit",
            "CI": "ContainerInherit",
            "I": "Inherited",
            "DENY": "Deny",
            "F": "FullControl",
            "M": "Modify",
            "RX": "ReadAndExecute",
            "DC": "DeleteSubdirectoriesAndFiles",
        }.get(value, value)


def _probe(directory: Path) -> ProbeResult:
    """对目录执行 create → write → read → delete 探针。"""
    result = ProbeResult(
        path=str(directory),
        exists=directory.is_dir(),
        create=False,
        write=False,
        read=False,
        delete=False,
    )
    if not result.exists:
        result.error = "目录不存在"
        return result

    sandbox = directory / f"__audit_{os.getpid()}"
    probe_file = sandbox / "probe.txt"
    try:
        sandbox.mkdir()
        result.create = True
        probe_file.write_text("audit", encoding="utf-8")
        result.write = True
        result.read = probe_file.read_text(encoding="utf-8") == "audit"
    except OSError as exc:
        result.error = str(exc)
    finally:
        try:
            if probe_file.exists():
                probe_file.unlink()
            if sandbox.exists():
                sandbox.rmdir()
            result.delete = not sandbox.exists()
        except OSError as exc:
            result.error = result.error or str(exc)
            result.delete = False
    return result


def _target_dirs(manager: PathManager) -> list[Path]:
    """参与探针的运行时目录（不含 resources：只读资源不应被写）。"""
    return [
        manager.root,
        manager.data,
        manager.html,
        manager.results,
        manager.models,
        manager.backups,
        manager.logs,
        manager.har,
        manager.output,
    ]


def _scan_readonly(root: Path) -> list[str]:
    """扫描只读属性文件（跳过 git / venv）。"""
    found: list[str] = []
    for path in root.rglob("*"):
        if any(part in _READONLY_SKIP for part in path.parts):
            continue
        try:
            if path.is_file() and not path.stat().st_mode & stat.S_IWRITE:
                found.append(str(path))
        except OSError:
            continue
    return found


def _scan_stale_temp() -> list[str]:
    """列出系统临时目录下的本项目残留目录。"""
    try:
        base = Path(tempfile.gettempdir())
        return sorted(str(path) for path in base.glob(f"{TEMP_PREFIX}*") if path.is_dir())
    except OSError:  # pragma: no cover
        return []


def _scan_caches(root: Path) -> list[dict[str, object]]:
    """统计可重建缓存目录的体积。"""
    rows: list[dict[str, object]] = []
    for name in _CACHE_DIRS:
        path = root / name
        if not path.is_dir():
            continue
        total = 0
        for entry in path.rglob("*"):
            try:
                if entry.is_file():
                    total += entry.stat().st_size
            except OSError:
                continue
        rows.append({"name": name, "size_mb": round(total / (1024 * 1024), 1)})
    return rows


def run_audit(root: Path) -> AuditReport:
    """执行完整审计。"""
    from mihoyo_toolkit.core.temp import temp_root

    manager = PathManager(root=root)
    acl, notes = _audit_acl(root)
    report = AuditReport(root=str(root), temp_root=str(temp_root()), acl=acl, notes=notes)
    report.probes = [_probe(directory) for directory in _target_dirs(manager)]
    report.readonly_files = _scan_readonly(root)
    report.stale_temp_dirs = _scan_stale_temp()
    report.cache_dirs = _scan_caches(root)
    return report


def _print_report(report: AuditReport) -> None:
    """打印人类可读报告。"""
    print("=" * 66)
    print(f"  工作区审计  {report.root}")
    print("=" * 66)
    print(f"临时根: {report.temp_root}")
    print(f"结论: {'通过' if report.ok else '存在失败项'}")

    print("\n[目录探针] create / write / read / delete")
    for probe in report.probes:
        flags = "".join(
            "OK " if value else "FAIL"
            for value in (probe.create, probe.write, probe.read, probe.delete)
        )
        print(f"  [{flags}] {probe.path}" + (f"  ({probe.error})" if probe.error else ""))

    print(f"\n[ACL] 共 {len(report.acl)} 条（仅拒绝条目需要关注）")
    for entry in report.acl:
        if entry.allow:
            continue
        kind = "ALLOW" if entry.allow else "DENY "
        mark = "预期" if entry.expected else "注意"
        inherited = "继承" if entry.inherited else "显式"
        print(f"  {kind} {mark} {inherited}  {entry.identity}: {entry.rights}")

    print(f"\n[只读文件] {len(report.readonly_files)}")
    for path in report.readonly_files[:20]:
        print(f"  {path}")

    print(f"\n[临时目录残留] {len(report.stale_temp_dirs)}")
    for path in report.stale_temp_dirs[:20]:
        print(f"  {path}")

    print(f"\n[可重建缓存] {len(report.cache_dirs)}")
    for row in report.cache_dirs:
        print(f"  {row['name']}: {row['size_mb']} MB")

    for note in report.notes:
        print(f"\n[说明] {note}")

    if report.failures:
        print("\n[失败项]")
        for problem in report.failures:
            print(f"  - {problem}")


def main(argv: list[str] | None = None) -> int:
    """脚本入口。"""
    parser = argparse.ArgumentParser(description="工作区权限 / 可写性审计（只读）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    parser.add_argument("--home", default=None, help="工作区根目录（默认自动探测）")
    args = parser.parse_args(argv)

    if args.home:
        root = Path(args.home).expanduser().resolve()
    else:
        from mihoyo_toolkit.core.paths import resolve_root

        root, _warning = resolve_root()

    report = run_audit(root)
    if args.json:
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    else:
        _print_report(report)
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
