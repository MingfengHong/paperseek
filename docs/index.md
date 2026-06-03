---
layout: home

hero:
  name: PaperSeek
  text: LLM based Literature Search Agent
  tagline: 用自然语言发起文献检索，自动迭代查询、扩展引用、排序结果，并导出可复核的候选论文列表。
  image:
    src: /paperseek-icon.svg
    alt: PaperSeek
  actions:
    - theme: brand
      text: 阅读开源版手册
      link: /user-manual
    - theme: alt
      text: 在线体验版说明
      link: /online-demo
    - theme: alt
      text: GitHub 仓库
      link: https://github.com/MingfengHong/paperseek

features:
  - title: 自然语言检索
    details: 输入中文或英文研究问题，由 LLM 生成适合 OpenAlex、Crossref 或 WoS Starter 的检索查询。
  - title: 可观察工作流
    details: 实时查看查询生成、数据源请求、检索式调整、结果排序、引用扩展和系统日志。
  - title: 引用扩展与图谱
    details: 基于 OpenAlex 扩展高匹配论文的参考文献和被引论文，并用箭头展示引用方向。
  - title: 可复核导出
    details: 在 Results 页面筛选、勾选、排序论文，导出包含元数据和评分理由的 CSV。
---

## 选择你的入口

PaperSeek 的社区文档分为两个主要入口：

- **开源自托管版**：阅读 [开源版完整用户手册](user-manual.md)，适合本地运行、Docker/VPS 部署、配置自己的 LLM Key 和数据源 Key。
- **在线体验版**：阅读 [在线体验版用户手册](online-demo.md)，适合直接访问 [paperseek.xyz](https://www.paperseek.xyz/) 试用完整 Web UI。

部署 Docker、Docker Compose 或 Vercel 时，阅读 [部署指南](deployment.md)。

## 社区维护方式

文档源码保存在 `main` 分支的 `docs/` 目录。GitHub Actions 构建后会把静态产物发布到 `gh-pages` 分支。`gh-pages` 只是 GitHub Pages 发布分支，不作为社区开发分支。
