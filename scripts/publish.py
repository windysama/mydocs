#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键把 D:\\文档 下的私有笔记发布到公开知识库 docs/。

自动完成上次出问题的所有环节：
  1. 复制 .md 的同时，自动携带同名 xxx.assets/ 目录（只拷该文实际引用的图片）
  2. 同时支持 Typora(.assets) / Obsidian(附件、attachments) 两种图床布局
  3. 把 Obsidian wikilink ![[a.png]] 自动转换成 MkDocs 可渲染的 ![](路径)
  4. 发布前跑敏感信息扫描；有 HIGH/MEDIUM 命中则中止（除非 --force）
  5. 发布后跑引用完整性检查，确保不会再出现「图片加载失败」
  6. 可选自动写入 mkdocs.yml 的 nav

用法：
  # 预演，什么都不改，只告诉你会发生什么（强烈建议先跑）
  python scripts/publish.py "D:\\文档\\巨蟹项目\\0.资料\\SONiC\\xxx.md" --dry-run

  # 正式发布
  python scripts/publish.py "D:\\文档\\...\\xxx.md"

  # 指定站内文件名 + 自动加进导航
  python scripts/publish.py "D:\\...\\xxx.md" --as sonic-gns3.md --nav "技术笔记"
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

RE_MD_IMAGE = re.compile(r"(!\[[^\]]*\]\()\s*([^)\s]+)((?:\s+\"[^\"]*\")?\s*\))")
RE_HTML_IMG = re.compile(r"(<img[^>]*\ssrc\s*=\s*[\"'])([^\"']+)([\"'])", re.I)
RE_WIKI_IMG = re.compile(r"!\[\[([^\]|]+?)(?:\|([^\]]*))?\]\]")
RE_WIKI_LINK = re.compile(r"(?<!\!)\[\[([^\]|]+?)(?:\|([^\]]*))?\]\]")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".avif"}

# 常见附件目录名（Obsidian 习惯）
ATTACH_DIR_NAMES = ["附件", "attachments", "assets", "images", "img", "_images"]


def log(msg: str) -> None:
    print(msg, flush=True)


def is_external(t: str) -> bool:
    p = urlsplit(t)
    return bool(p.scheme or p.netloc) or t.startswith(("#", "data:", "mailto:", "//"))


def find_vault_root(md: Path, depth: int = 6) -> Path:
    """向上找 Obsidian vault 根（含 .obsidian），找不到就用所在目录。"""
    cur = md.parent
    for _ in range(depth):
        if (cur / ".obsidian").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return md.parent


def locate_attachment(name: str, md: Path, vault: Path) -> Path | None:
    """按 Obsidian 解析规则找附件：同目录 -> 常见附件目录 -> 全 vault 搜索。"""
    name = unquote(name).strip()
    cand = Path(name)

    # 直接相对路径命中
    for base in (md.parent, vault):
        p = (base / cand)
        if p.is_file():
            return p.resolve()

    # 常见附件目录
    for d in ATTACH_DIR_NAMES:
        for base in (md.parent, vault):
            p = base / d / cand.name
            if p.is_file():
                return p.resolve()

    # 全 vault 按文件名搜索（Obsidian 的短链接行为）
    matches = [p for p in vault.rglob(cand.name) if p.is_file()]
    if len(matches) == 1:
        return matches[0].resolve()
    if matches:
        return sorted(matches, key=lambda p: len(str(p)))[0].resolve()
    return None


def run(cmd: list[str], cwd: Path) -> int:
    log(f"    $ {' '.join(cmd[1:]) if cmd[0] == sys.executable else ' '.join(cmd)}")
    return subprocess.call(cmd, cwd=str(cwd))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="源 Markdown 文件（D:\\文档 下）")
    ap.add_argument("--repo", default=None, help="仓库根目录（默认脚本上一级）")
    ap.add_argument("--as", dest="dest_name", default=None,
                    help="发布后的文件名，默认沿用源文件名")
    ap.add_argument("--nav", default=None,
                    help="加入 mkdocs.yml nav 的分组标题，如 技术笔记")
    ap.add_argument("--title", default=None, help="nav 中显示的标题，默认用文件名")
    ap.add_argument("--dry-run", action="store_true", help="预演，不写任何文件")
    ap.add_argument("--force", action="store_true",
                    help="即使敏感信息扫描不通过也继续（危险）")
    ap.add_argument("--allow-medium", action="store_true",
                    help="内网 IP 等 MEDIUM 项仅告警")
    args = ap.parse_args()

    src = Path(args.source).expanduser()
    if not src.is_file():
        log(f"[FAIL] 源文件不存在: {src}")
        return 2

    repo = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parent.parent
    docs = repo / "docs"
    if not docs.is_dir():
        log(f"[FAIL] 找不到 docs 目录: {docs}")
        return 2

    dest_name = args.dest_name or src.name
    if not dest_name.endswith(".md"):
        dest_name += ".md"
    dest = docs / dest_name
    assets_dirname = dest.stem + ".assets"
    assets_dir = docs / assets_dirname

    vault = find_vault_root(src)
    text = src.read_text(encoding="utf-8", errors="replace")

    log(f"源文件 : {src}")
    log(f"目标   : {dest}")
    log(f"图床   : docs/{assets_dirname}/")
    log(f"vault  : {vault}")
    log("")

    copies: dict[Path, str] = {}   # 源图片 -> 目标文件名
    problems: list[str] = []
    used_names: set[str] = set()

    def register(srcimg: Path) -> str:
        """登记一张图片，返回它在 assets 目录下的文件名（自动去重）。"""
        if srcimg in copies:
            return copies[srcimg]
        base = srcimg.name
        stem, suf = Path(base).stem, Path(base).suffix
        final = base
        i = 1
        while final in used_names:
            final = f"{stem}-{i}{suf}"
            i += 1
        used_names.add(final)
        copies[srcimg] = final
        return final

    # ---- 1) 转换 wikilink 图片 ------------------------------------------
    def sub_wiki_img(m: re.Match) -> str:
        target, alias = m.group(1), (m.group(2) or "")
        found = locate_attachment(target, src, vault)
        if not found:
            problems.append(f"wikilink 图片找不到源文件: ![[{target}]]")
            return m.group(0)
        name = register(found)
        alt = alias.strip() or Path(target).stem
        return f"![{alt}]({quote(assets_dirname)}/{quote(name)})"

    new_text, n_wiki = RE_WIKI_IMG.subn(sub_wiki_img, text)

    # ---- 2) 处理标准图片引用 -------------------------------------------
    def sub_md_img(m: re.Match) -> str:
        head, target, tail = m.group(1), m.group(2), m.group(3)
        if is_external(target):
            return m.group(0)
        rel = unquote(urlsplit(target).path)
        found = (src.parent / rel)
        if not found.is_file():
            alt = locate_attachment(Path(rel).name, src, vault)
            if not alt:
                problems.append(f"图片找不到源文件: {target}")
                return m.group(0)
            found = alt
        name = register(found.resolve())
        return f"{head}{quote(assets_dirname)}/{quote(name)}{tail}"

    new_text, n_md = RE_MD_IMAGE.subn(sub_md_img, new_text)

    def sub_html_img(m: re.Match) -> str:
        head, target, tail = m.group(1), m.group(2), m.group(3)
        if is_external(target):
            return m.group(0)
        rel = unquote(urlsplit(target).path)
        found = (src.parent / rel)
        if not found.is_file():
            alt = locate_attachment(Path(rel).name, src, vault)
            if not alt:
                problems.append(f"HTML <img> 找不到源文件: {target}")
                return m.group(0)
            found = alt
        name = register(found.resolve())
        return f"{head}{quote(assets_dirname)}/{quote(name)}{tail}"

    new_text, n_html = RE_HTML_IMG.subn(sub_html_img, new_text)

    # ---- 3) 非图片 wikilink（文档互链）降级为纯文本，避免站上出现乱码 ----
    def sub_wiki_link(m: re.Match) -> str:
        target, alias = m.group(1), (m.group(2) or "")
        shown = alias.strip() or target.strip()
        problems.append(
            f"文档互链 [[{target}]] 无法自动解析，已转为纯文本「{shown}」"
            f"（如需跳转请手动改成 [{shown}](目标.md)）")
        return shown

    new_text, n_wl = RE_WIKI_LINK.subn(sub_wiki_link, new_text)

    log(f"引用转换：wikilink 图片 {n_wiki} 处，标准图片 {n_md} 处，"
        f"HTML img {n_html} 处，文档互链 {n_wl} 处")
    log(f"待复制图片：{len(copies)} 张")
    for s, d in sorted(copies.items(), key=lambda kv: kv[1]):
        log(f"    {d}  <-  {s}")
    if problems:
        log("")
        for p in problems:
            log(f"  [!] {p}")
    log("")

    # ---- 4) 敏感信息预检（在临时内容上跑，未落盘也能拦） ----------------
    scanner = repo / "scripts" / "scan_secrets.py"
    if scanner.is_file():
        tmp = repo / ".publish_precheck.md"
        tmp.write_text(new_text, encoding="utf-8")
        try:
            cmd = [sys.executable, str(scanner), "--path", str(tmp)]
            if args.allow_medium:
                cmd.append("--allow-medium")
            log("=== 敏感信息扫描 ===")
            rc = subprocess.call(cmd, cwd=str(repo))
        finally:
            tmp.unlink(missing_ok=True)
        log("")
        if rc != 0 and not args.force:
            log("[ABORT] 敏感信息检查未通过，已取消发布。")
            log("        确认可公开后，用 --allow-medium 或按提示加 allowlist 注释；"
                "或 --force 强行发布（不推荐）。")
            return 1
        if rc != 0 and args.force:
            log("[WARN] --force 已指定，忽略敏感信息告警继续发布。")

    if args.dry_run:
        log("[DRY-RUN] 预演结束，未修改任何文件。")
        return 0

    # ---- 5) 落盘 -------------------------------------------------------
    if copies:
        assets_dir.mkdir(parents=True, exist_ok=True)
    for s, d in copies.items():
        shutil.copy2(s, assets_dir / d)
    dest.write_text(new_text, encoding="utf-8", newline="\n")
    log(f"[OK] 已写入 {dest.relative_to(repo)}")
    if copies:
        log(f"[OK] 已复制 {len(copies)} 张图片到 docs/{assets_dirname}/")

    # ---- 6) 可选：写 nav ----------------------------------------------
    if args.nav:
        mk = repo / "mkdocs.yml"
        content = mk.read_text(encoding="utf-8")
        title = args.title or dest.stem
        entry = f"      - {title}: {dest_name}"
        if dest_name in content:
            log(f"[SKIP] mkdocs.yml 中已存在 {dest_name}，未改动 nav")
        else:
            lines = content.splitlines()
            out, inserted = [], False
            for i, ln in enumerate(lines):
                out.append(ln)
                if not inserted and ln.strip().rstrip(":") == f"- {args.nav}".rstrip(":") \
                   or (not inserted and ln.strip() == f"- {args.nav}:"):
                    out.append(entry)
                    inserted = True
            if inserted:
                mk.write_text("\n".join(out) + "\n", encoding="utf-8")
                log(f"[OK] 已在 nav「{args.nav}」下加入 {title}")
            else:
                log(f"[WARN] mkdocs.yml 中未找到分组「{args.nav}」，请手动添加：\n{entry}")

    # ---- 7) 发布后完整性校验 ------------------------------------------
    checker = repo / "scripts" / "check_assets.py"
    if checker.is_file():
        log("")
        log("=== 引用完整性校验 ===")
        rc = subprocess.call([sys.executable, str(checker)], cwd=str(repo))
        if rc != 0:
            log("[FAIL] 校验未通过，请修正后再提交。")
            return 1

    log("")
    log("完成。下一步：")
    log("  git add -A")
    log(f'  git commit -m "docs: 新增 {dest.stem}"')
    log("  git push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
