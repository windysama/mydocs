# 发布工作流说明

私有笔记写在 `D:\文档`，筛选后发布到本仓库 `docs/` 公开。
`scripts/` 下三个脚本负责把这个流程自动化，并防住两类事故：
**图片没带上导致线上 404**、**内网信息/密钥误发到公网**。

---

## 日常发布：一条命令

```powershell
cd D:\codehub\workspace\mydocs

# 1) 先预演：不改任何文件，只看会复制哪些图、有没有敏感信息
python scripts\publish.py "D:\文档\某项目\某文章.md" --dry-run

# 2) 确认无误后正式发布
python scripts\publish.py "D:\文档\某项目\某文章.md"

# 3) 提交
git add -A
git commit -m "docs: 新增 某文章"
git push
```

`publish.py` 会自动：

| 动作 | 说明 |
|---|---|
| 携带图片 | 自动找到该文引用的每张图，复制到 `docs/<文章名>.assets/` |
| 兼容两种图床 | Typora 的 `xxx.assets/` 与 Obsidian 的 `附件/`、`attachments/` 都支持 |
| 转换 wikilink | `![[图.png]]` → `![图](xxx.assets/图.png)`（MkDocs 不认前者） |
| 发布前安检 | 跑敏感信息扫描，有高危项直接中止 |
| 发布后校验 | 跑引用完整性检查，确保不会再出现图片加载失败 |

常用参数：

```powershell
--as sonic.md              # 指定站内文件名（建议用英文名，URL 更干净）
--nav "技术笔记"            # 自动加进 mkdocs.yml 的导航分组
--title "SONiC 环境搭建"    # 导航里显示的标题
--allow-medium             # 内网 IP 等只告警，不阻断（确认可公开时用）
--force                    # 强行发布，忽略安检（不推荐）
```

---

## 敏感信息扫描

```powershell
python scripts\scan_secrets.py                    # 扫 docs/
python scripts\scan_secrets.py --path 单个文件.md   # 发布前单独查
```

三个级别：

- **HIGH（必拦）**：私钥、AWS AK、GitHub token、URL 内嵌账号密码、真实口令赋值
- **MEDIUM（默认拦）**：内网 IP（`10.` / `172.16-31.` / `192.168.`）、内部域名、公司项目代号
- **LOW（提示）**：邮箱地址

已针对本仓库实际内容做过降噪，**不会误报**这些：

- SONiC/GNS3 公开默认口令（如 `YourPaSsWoRd`）、占位符（`<PASSWORD>`、`$VAR`）
- `127.0.0.1`、`0.0.0.0`、文档示例网段 `192.0.2.x`
- `vncpasswd` 这类交互式命令、`http://host:3080` 里的端口号
- `root@1.2.3.4` 这类 ssh 目标（不会当成邮箱）

**确认某处可以公开**时，加豁免注释：

```markdown
内部测试机 10.0.0.5 <!-- allowlist secret 已停用的实验机，可公开 -->
```

整篇文件豁免（放在文件开头）：

```markdown
<!-- allowlist-file -->
```

---

## 图片/链接完整性检查

```powershell
python scripts\check_assets.py
python scripts\check_assets.py --strict-orphans   # 把「多余图片」也当错误
```

检查失效图片、失效本地链接、残留的 wikilink，并提示未被引用的孤立图片。

---

## CI 门禁

`.github/workflows/ci.yml` 中 `check` 任务会在每次 push / PR 上运行上述两个脚本，
**只有通过才会执行 `mkdocs gh-deploy`**。这样即使忘了本地检查，也不会把坏页面发上线。

CI 中内网 IP 用 `--allow-medium` 只告警（否则现有文档会直接失败），
但密钥、token、真实口令一旦出现就会**中断部署**。

---

## 注意：两处文档已分叉

`D:\文档` 下的源文件与 `docs/` 内的副本内容已不一致（源文件更完整）。
建议**始终以 `D:\文档` 为唯一写作源**，需要更新公开版时重新跑一次 `publish.py` 覆盖，
避免两边各改一半。
