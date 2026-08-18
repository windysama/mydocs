---
hide:
  - toc
---

<!-- Hero 区 -->
<section class="mdx-container">
  <div class="md-grid md-typeset">
    <div class="mdx-hero">
      <div class="mdx-hero__content">
        <h1>windysama 的文档站</h1>
        <p>
          记录 Linux 内核 <strong>RDMA 网卡驱动</strong>、固件与芯片层面验证的技术笔记，
          以及日常开发调试心得。
        </p>
        <a href="rdma-notes/" class="md-button md-button--primary">
          :material-server-network: 浏览技术笔记
        </a>
        <a href="about/" class="md-button">
          :material-account-circle: 关于我
        </a>
      </div>
    </div>
  </div>
</section>

<!-- 统计条 -->
<div class="mdx-stats">
  <div class="mdx-stat"><span class="mdx-stat__num">3</span><span class="mdx-stat__label">技术文档</span></div>
  <div class="mdx-stat"><span class="mdx-stat__num">2</span><span class="mdx-stat__label">主题模式</span></div>
  <div class="mdx-stat"><span class="mdx-stat__num">∞</span><span class="mdx-stat__label">持续更新</span></div>
  <div class="mdx-stat"><span class="mdx-stat__num">CI</span><span class="mdx-stat__label">自动部署</span></div>
</div>

## 站点内容

本站基于 **GitHub Pages + MkDocs Material** 搭建，文档源码全部用 Markdown 编写，
每次 `git push` 到 `main` 分支即自动构建发布。

<div class="grid cards" markdown>

- :material-server-network:{ .lg .middle } __RDMA 技术笔记__

    ---

    RDMA 网卡驱动在内核中的实现要点，以及 firmware / 芯片层面的验证思路与调试手段。

    [:octicons-arrow-right-24: 阅读笔记](rdma-notes.md)

- :material-rocket-launch:{ .lg .middle } __快速开始__

    ---

    本地搭建同款文档站：安装依赖后，一条命令即可本地预览。

    [:octicons-arrow-right-24: 查看命令](#quick-start)

- :material-account:{ .lg .middle } __关于我__

    ---

    专注 Linux 内核 RDMA 网卡驱动的工程师，欢迎交流指正。

    [:octicons-arrow-right-24: 了解更多](about.md)

</div>

## 快速开始（本地预览） {#quick-start}

```bash
pip install -r requirements.txt
mkdocs serve          # 打开 http://127.0.0.1:8000
```

!!! tip "想新增一篇文档？"
    在 `docs/` 下新建 `.md` 文件，并在 `mkdocs.yml` 的 `nav` 中登记，
    推送后 GitHub Actions 会自动构建并上线。
