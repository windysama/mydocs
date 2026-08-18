# mydocs

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-在线-0d2b45?logo=github&logoColor=white)](https://windysama.github.io/mydocs/)
[![deploy](https://github.com/windysama/mydocs/actions/workflows/ci.yml/badge.svg)](https://github.com/windysama/mydocs/actions/workflows/ci.yml)
[![MkDocs Material](https://img.shields.io/badge/MkDocs-Material-526cfe?logo=readthedocs&logoColor=white)](https://squidfunk.github.io/mkdocs-material/)

个人技术文档站 —— 基于 **GitHub Pages + MkDocs Material** 搭建，
专注 Linux 内核 **RDMA 网卡驱动**、固件验证与调试笔记。

- 源码（Markdown）：[docs/](docs/)
- 站点配置：[mkdocs.yml](mkdocs.yml)
- 自动部署：[.github/workflows/ci.yml](.github/workflows/ci.yml)
- 依赖清单：[requirements.txt](requirements.txt)
- 线上地址：<https://windysama.github.io/mydocs/>

## 本地预览

```bash
pip install -r requirements.txt
mkdocs serve          # 打开 http://127.0.0.1:8000
```

## 如何新增一篇文档

1. 在 [docs/](docs/) 下新建 `.md` 文件，记得在文件头部写 `tags` 与标题；
2. 在 [mkdocs.yml](mkdocs.yml) 的 `nav` 中登记路径；
3. `git push` 到 `main`，GitHub Actions 会自动构建并部署到 Pages。
