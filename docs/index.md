# windysama 的文档站

欢迎来到我的个人技术文档站。这里主要存放我自己整理的技术笔记与文档，
涵盖 RDMA 网卡驱动、固件验证以及相关内核调试经验。

## 这个站点怎么来的

本站基于 **GitHub Pages + MkDocs Material** 搭建：

- 文档源码全部用 Markdown 编写，托管在
  [windysama/mydocs](https://github.com/windysama/mydocs) 仓库；
- 每次 `git push` 到 `main` 分支，GitHub Actions 自动执行
  `mkdocs build` 并部署到 GitHub Pages；
- 网站地址：`https://windysama.github.io/mydocs/`。

## 你可以做什么

- 使用左侧导航浏览文档；
- 右上角可切换 **亮色 / 暗色** 主题；
- 顶部搜索框支持全文检索；
- 代码块右上角有复制按钮。

## 快速开始（本地预览）

```bash
pip install mkdocs-material
mkdocs serve          # 打开 http://127.0.0.1:8000
```

> 想新增一篇文档？在 `docs/` 下新建 `.md` 文件，并在 `mkdocs.yml`
> 的 `nav` 中登记即可，推送后自动上线。
