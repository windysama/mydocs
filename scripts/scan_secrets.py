#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发布前敏感信息扫描：防止内网 IP、主机名、口令、密钥、公司标识被推到公网。

设计要点（按 windysama 的实际文档校准）：
  * 内网 IP（10./172.16-31./192.168.）视为敏感；127.0.0.1、0.0.0.0、示例网段放行
  * SONiC/GNS3 等「公开默认口令」不误报，真实赋值口令才报
  * 支持行内豁免注释：  <!-- allowlist secret 说明理由 -->
  * 支持整文件豁免：文件头部加  <!-- allowlist-file -->

严重级别：
  HIGH   —— 必须处理，CI 直接失败（私钥、AK/SK、真实口令赋值）
  MEDIUM —— 默认失败，可用 --allow-medium 降级为告警（内网 IP、内部主机名）
  LOW    —— 仅提示

用法：
  python scripts/scan_secrets.py                 # 扫 docs/
  python scripts/scan_secrets.py --path 某文件.md  # 扫单个文件（发布前预检）
  python scripts/scan_secrets.py --allow-medium   # 内网 IP 只告警
"""
from __future__ import annotations

import argparse
import ipaddress
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Windows 控制台默认 GBK，直接 print 中文/emoji 会抛 UnicodeEncodeError。
# 统一切到 UTF-8，并对无法编码的字符降级而不是崩溃。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HIGH, MEDIUM, LOW = "HIGH", "MEDIUM", "LOW"

# 公开的、写进文档无害的默认口令（SONiC / GNS3 / 常见镜像）
PUBLIC_DEFAULT_SECRETS = {
    "yourpassword", "yourpasswd", "admin", "password", "passwd", "123456",
    "root", "changeme", "public", "private", "guest", "test", "example",
    "your_password", "your-password", "<password>", "xxx", "xxxx", "***",
    "yourpaswword", "yourpasword", "yourpaSsWoRd".lower(), "sonic", "gns3",
}

# 占位符特征：明显不是真实凭据
RE_PLACEHOLDER = re.compile(
    r"^(<.*>|\{\{.*\}\}|\$\{?[A-Z_][A-Z0-9_]*\}?|\*+|x{3,}|\.{3,}|"
    r"your[_-]?\w*|my[_-]?\w*|some[_-]?\w*|abc123|foo|bar|todo|tbd|n/?a)$",
    re.I,
)

RE_FENCE = re.compile(r"(?ms)^(?P<fence>```+|~~~+).*?^(?P=fence)\s*$")
RE_ALLOW_LINE = re.compile(r"<!--\s*allowlist(?:\s+secret)?\b[^>]*-->", re.I)
RE_ALLOW_FILE = re.compile(r"<!--\s*allowlist-file\b[^>]*-->", re.I)


@dataclass
class Rule:
    name: str
    regex: re.Pattern
    level: str
    hint: str
    group: int = 0


RULES: list[Rule] = [
    # ---------- HIGH：真实凭据 ----------
    Rule("私钥文件内容",
         re.compile(r"-----BEGIN\s+(?:RSA|DSA|EC|OPENSSH|PGP)?\s*PRIVATE KEY"),
         HIGH, "私钥绝不能进公开仓库；请立即轮换该密钥"),
    Rule("AWS Access Key",
         re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), HIGH, "撤销并轮换该 AK"),
    Rule("GitHub Token",
         re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}\b"), HIGH, "立即吊销该 token"),
    Rule("Slack/Bot Token",
         re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"), HIGH, "立即吊销"),
    Rule("私有 PyPI/npm 凭据 URL",
         re.compile(r"://[^/\s:@]+:[^/\s:@]+@[\w.-]+"), HIGH,
         "URL 内嵌账号密码，请改用环境变量或凭据管理器"),
    Rule("口令赋值",
         re.compile(
             r"(?i)\b(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|"
             r"secret[_-]?key|credential|口令|密码)\s*[:=]\s*"
             r"[\"']?([^\s\"',;#]{4,})[\"']?"),
         HIGH, "疑似真实口令；改为占位符或引用环境变量", group=1),

    # ---------- MEDIUM：内网拓扑 ----------
    Rule("内网 IP 地址",
         re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), MEDIUM,
         "暴露内网拓扑；建议改为 <SERVER_IP> 或文档示例网段 192.0.2.x"),
    Rule("内部主机名/域名",
         re.compile(r"(?i)\b[\w-]+\.(?:corp|intra|internal|local|lan|"
                    r"starsmicrosystem)\.?[\w.]*\b"),
         MEDIUM, "暴露内部域名；建议脱敏"),
    Rule("内部代号/涉密标识",
         re.compile(r"(?i)(天蝎|巨蟹|Scorpio|绝密|机密|内部资料|仅限内部|confidential)"),
         MEDIUM, "疑似公司内部项目代号或涉密标识，确认可公开后再豁免"),

    # ---------- LOW ----------
    Rule("邮箱地址",
         re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), LOW,
         "如为公司邮箱建议脱敏"),
]

# 允许出现的「非敏感」IP
SAFE_IP_EXACT = {
    "0.0.0.0", "127.0.0.1", "255.255.255.255", "8.8.8.8", "1.1.1.1",
    "169.254.169.254",
}


def ip_is_sensitive(text: str) -> bool:
    if text in SAFE_IP_EXACT:
        return False
    try:
        ip = ipaddress.IPv4Address(text)
    except ValueError:
        return False  # 版本号之类，不是 IP
    if ip.is_loopback or ip.is_unspecified or ip.is_multicast or ip.is_link_local:
        return False
    # RFC5737 文档示例网段：鼓励使用
    if ip in ipaddress.ip_network("192.0.2.0/24") or \
       ip in ipaddress.ip_network("198.51.100.0/24") or \
       ip in ipaddress.ip_network("203.0.113.0/24"):
        return False
    if ip.is_private:
        return True          # 10./172.16-31./192.168. -> 内网，报
    return False             # 公网 IP（如镜像源）不报


def looks_public_default(value: str) -> bool:
    v = value.strip().strip("`\"'")
    if v.lower() in PUBLIC_DEFAULT_SECRETS:
        return True
    if RE_PLACEHOLDER.match(v):
        return True
    # 纯变量引用 / 命令替换
    if v.startswith("$") or v.startswith("${") or v.startswith("$("):
        return True
    return False


def code_mask(text: str) -> set[int]:
    """返回位于代码块内的行号集合（供降噪判断，不直接跳过）。"""
    lines: set[int] = set()
    for m in RE_FENCE.finditer(text):
        start = text.count("\n", 0, m.start()) + 1
        end = text.count("\n", 0, m.end()) + 1
        lines.update(range(start, end + 1))
    return lines


@dataclass
class Finding:
    file: str
    line: int
    level: str
    rule: str
    excerpt: str
    hint: str


def scan_text(rel: str, text: str) -> list[Finding]:
    if RE_ALLOW_FILE.search(text):
        return []

    out: list[Finding] = []
    lines = text.splitlines()
    in_code = code_mask(text)

    for idx, line in enumerate(lines, start=1):
        if RE_ALLOW_LINE.search(line):
            continue
        if line.lstrip().startswith("<!--"):
            continue

        for rule in RULES:
            for m in rule.regex.finditer(line):
                value = m.group(rule.group) if rule.group else m.group(0)

                if rule.name == "内网 IP 地址":
                    if not ip_is_sensitive(value):
                        continue
                elif rule.name == "口令赋值":
                    if looks_public_default(value):
                        continue
                    # vncpasswd / passwd 这类交互命令没有真实值
                    if re.search(r"(?i)\b(vnc)?passwd\s*$", line.strip()):
                        continue
                elif rule.name == "邮箱地址":
                    if value.endswith(("users.noreply.github.com", "example.com")):
                        continue
                    # user@1.2.3.4 是 ssh/scp 目标，不是邮箱（IP 规则已单独覆盖）
                    domain = value.rsplit("@", 1)[-1]
                    if re.fullmatch(r"(?:\d{1,3}\.){3}\d{1,3}", domain):
                        continue
                elif rule.name == "私有 PyPI/npm 凭据 URL":
                    # http://host:3080/ 这类端口号不是密码
                    if re.match(r"^://[^/\s:@]+:\d+", m.group(0)):
                        continue

                snippet = line.strip()
                if len(snippet) > 160:
                    snippet = snippet[:157] + "..."

                level = rule.level
                # 代码块里的内部代号多为路径/命令噪声，降一档
                if rule.name == "内部代号/涉密标识" and idx in in_code:
                    level = LOW

                out.append(Finding(rel, idx, level, rule.name, snippet, rule.hint))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default="docs",
                    help="要扫描的文件或目录（默认 docs）")
    ap.add_argument("--allow-medium", action="store_true",
                    help="MEDIUM 仅告警，不导致失败")
    ap.add_argument("--fail-on-low", action="store_true",
                    help="LOW 也视为失败")
    args = ap.parse_args()

    target = Path(args.path)
    if not target.exists():
        print(f"[FAIL] 路径不存在: {target}")
        return 2

    files = [target] if target.is_file() else sorted(target.rglob("*.md"))

    findings: list[Finding] = []
    for f in files:
        rel = f.name if target.is_file() else f.relative_to(target).as_posix()
        findings.extend(scan_text(rel, f.read_text(encoding="utf-8", errors="replace")))

    print(f"敏感信息扫描：检查 {len(files)} 个文件")

    if not findings:
        print("[OK] 未发现敏感信息。")
        return 0

    order = {HIGH: 0, MEDIUM: 1, LOW: 2}
    findings.sort(key=lambda f: (order[f.level], f.file, f.line))

    icons = {HIGH: "[!!]", MEDIUM: "[!]", LOW: "[i]"}
    for f in findings:
        print(f"\n{icons[f.level]} [{f.level}] {f.rule}  -  {f.file}:{f.line}")
        print(f"    {f.excerpt}")
        print(f"    → {f.hint}")

    n_high = sum(1 for f in findings if f.level == HIGH)
    n_med = sum(1 for f in findings if f.level == MEDIUM)
    n_low = sum(1 for f in findings if f.level == LOW)
    print(f"\n合计：HIGH={n_high}  MEDIUM={n_med}  LOW={n_low}")
    print("确认某处可以公开时，在该行行尾加： <!-- allowlist secret 理由 -->")

    fail = n_high > 0 or (n_med > 0 and not args.allow_medium) or \
           (n_low > 0 and args.fail_on_low)
    if fail:
        print("\n[FAIL] 存在需要处理的敏感信息。")
        return 1
    print("\n[OK] 仅存在可接受级别的提示。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
