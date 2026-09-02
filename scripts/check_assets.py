#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
校验 docs/ 下所有 Markdown 的图片与本地链接引用是否真实存在。

用途：CI 门禁。发现失效引用即以非 0 退出，阻止构建出「图片加载失败」的站点。

检查项：
  1. 标准图片引用 ![alt](path)          -> 文件必须存在
  2. HTML <img src="...">               -> 文件必须存在
  3. Obsidian wikilink ![[...]]         -> MkDocs 不支持，直接报错
  4. 本地相对链接 [text](path.md)       -> 目标必须存在
  5. 孤立图片（存在但没被任何文档引用） -> 仅告警，不失败

用法：
  python scripts/check_assets.py
  python scripts/check_assets.py --docs docs --strict-orphans
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

# Windows 控制台默认 GBK，输出中文路径会乱码/报错，统一切到 UTF-8。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---- 匹配规则 ---------------------------------------------------------------
# ![alt](target)  —— 允许 target 里出现转义括号
RE_MD_IMAGE = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")
# [text](target) —— 普通链接（排除前面紧跟 ! 的图片）
RE_MD_LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(\s*([^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")
RE_HTML_IMG = re.compile(r"<img[^>]*\ssrc\s*=\s*[\"']([^\"']+)[\"']", re.I)
RE_WIKILINK = re.compile(r"!?\[\[([^\]]+)\]\]")

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".avif"}
# 代码块：```...``` 与 ~~~...~~~，以及行内 `code`
RE_FENCE = re.compile(r"(?ms)^(?P<fence>```+|~~~+).*?^(?P=fence)\s*$")
RE_INLINE_CODE = re.compile(r"`[^`\n]*`")


def strip_code(text: str) -> str:
    """把代码块/行内代码替换成等长空白，保持行号不变，避免误报。"""
    def blank(m: re.Match) -> str:
        return re.sub(r"[^\n]", " ", m.group(0))

    return RE_INLINE_CODE.sub(blank, RE_FENCE.sub(blank, text))


def is_external(target: str) -> bool:
    parts = urlsplit(target)
    if parts.scheme or parts.netloc:
        return True
    return target.startswith(("#", "mailto:", "data:", "//"))


def resolve(md_file: Path, docs_root: Path, target: str) -> Path:
    """把引用解析为磁盘路径（去掉 #anchor / ?query，做 percent-decode）。"""
    clean = unquote(urlsplit(target).path)
    if clean.startswith("/"):
        return (docs_root / clean.lstrip("/")).resolve()
    return (md_file.parent / clean).resolve()


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", default="docs", help="文档根目录（默认 docs）")
    ap.add_argument("--strict-orphans", action="store_true",
                    help="把「孤立图片」也视为错误")
    args = ap.parse_args()

    docs_root = Path(args.docs).resolve()
    if not docs_root.is_dir():
        print(f"[FAIL] 找不到文档目录: {docs_root}")
        return 2

    md_files = sorted(docs_root.rglob("*.md"))
    if not md_files:
        print(f"[WARN] {docs_root} 下没有 Markdown 文件")

    errors: list[str] = []
    warnings: list[str] = []
    referenced: set[Path] = set()
    checked = 0

    for md in md_files:
        rel_md = md.relative_to(docs_root).as_posix()
        raw = md.read_text(encoding="utf-8", errors="replace")
        body = strip_code(raw)

        # 3) Obsidian wikilink：MkDocs 渲染不了，必须拦下
        for m in RE_WIKILINK.finditer(body):
            errors.append(
                f"{rel_md}:{line_of(body, m.start())}  "
                f"Obsidian wikilink 语法不被 MkDocs 支持 -> {m.group(0).strip()}\n"
                f"    修正为: ![说明](相对路径/图片.png)"
            )

        # 1) + 2) 图片
        for regex, kind in ((RE_MD_IMAGE, "图片"), (RE_HTML_IMG, "HTML <img>")):
            for m in regex.finditer(body):
                target = m.group(1).strip()
                if is_external(target):
                    continue
                checked += 1
                path = resolve(md, docs_root, target)
                if path.is_file():
                    referenced.add(path)
                else:
                    errors.append(
                        f"{rel_md}:{line_of(body, m.start())}  "
                        f"{kind}缺失 -> {target}\n"
                        f"    期望文件: {path}"
                    )

        # 4) 本地链接（.md / 目录 / 附件）
        for m in RE_MD_LINK.finditer(body):
            target = m.group(1).strip()
            if is_external(target):
                continue
            path = resolve(md, docs_root, target)
            if path.suffix.lower() in IMAGE_SUFFIXES or path.suffix.lower() == ".md":
                checked += 1
                if path.exists():
                    referenced.add(path)
                else:
                    errors.append(
                        f"{rel_md}:{line_of(body, m.start())}  "
                        f"链接目标缺失 -> {target}\n"
                        f"    期望文件: {path}"
                    )

    # 5) 孤立图片
    all_images = {
        p.resolve()
        for p in docs_root.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    }
    orphans = sorted(all_images - referenced)
    for o in orphans:
        msg = f"{o.relative_to(docs_root).as_posix()}  图片未被任何文档引用（多余文件？）"
        (errors if args.strict_orphans else warnings).append(msg)

    # ---- 报告 --------------------------------------------------------------
    print(f"扫描 {len(md_files)} 个 Markdown，校验 {checked} 处引用，"
          f"发现图片 {len(all_images)} 张")

    for w in warnings:
        print(f"[WARN] {w}")

    if errors:
        print(f"\n[FAIL] 发现 {len(errors)} 个问题：\n")
        for e in errors:
            print(f"  x {e}")
        print("\n提示：用 scripts/publish.py 发布可自动携带 .assets 目录并转换 wikilink。")
        return 1

    print("[OK] 所有引用均可解析，无失效图片/链接。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
