# PaperSeek 文档源码

本目录是 PaperSeek 文档站源码目录，使用 VitePress 构建。社区贡献仍然修改 `main` 分支中的 `docs/`、`README.md` 和 `README.en.md`；构建后的静态产物由 GitHub Actions 发布到 `gh-pages` 分支。

## 文档入口

- [文档站首页](index.md)：VitePress 首页。
- [英文 README](https://github.com/MingfengHong/paperseek/blob/main/README.en.md)：面向国际社区的项目介绍和快速开始。
- [在线体验版使用说明](online-demo.md)：说明主站在线体验的 PaperSeek Service、Third-party Service（ModelScope、OpenRouter、Hugging Face）、Bring your own Key / BYOK、Source Filter、登录权限、第三方推理额度、历史记录和与自托管版的区别。
- [用户手册](user-manual.md)：从安装、快速开始、配置、模型、数据源、Discipline Fields、CLI、Web UI、中英文界面、导出、Skill、MCP Server 到排错的完整说明。
- [部署指南](deployment.md)：Docker、Docker Compose、Vercel 和 ModelScope 创空间部署说明。
- [文档站维护说明](site-maintenance.md)：说明 `main` 与 `gh-pages` 的分工、CI 发布规则和分支约束。
- [界面截图](assets/paperseek-web.png)：README 与社区展示使用的 Web UI 预览图。

## 本地预览

在仓库根目录运行：

```bash
npm install
npm run docs:dev
```

构建静态站点：

```bash
npm run docs:build
```

## 版本说明

当前文档面向 PaperSeek `0.1.x` alpha 版本。命令行参数和界面字段以当前仓库 `main` 分支为准。
