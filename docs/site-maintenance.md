# 文档站维护说明

PaperSeek 文档站使用 VitePress 构建。文档源码和发布产物分开管理：

| 分支 | 用途 |
| --- | --- |
| `main` | 社区开发分支。保存源码、Python 包、测试、README、`docs/` 文档源码和 VitePress 配置。 |
| `gh-pages` | GitHub Pages 静态发布分支。只保存构建后的站点产物，不作为开发分支。 |

## 贡献路径

社区贡献应提交到 `main`：

- 修改 `README.md`、`README.en.md`。
- 修改 `docs/` 下的用户手册、在线体验说明、部署指南和文档站配置。
- 通过 Pull Request 触发 Python CI 和文档构建检查。

不要直接向 `gh-pages` 提交社区文档源码。`gh-pages` 的内容由 GitHub Actions 生成。

## 发布规则

`.github/workflows/docs.yml` 在以下文件变化时运行：

- `docs/**`
- `README.md`
- `README.en.md`
- `package.json`
- `package-lock.json`
- `.github/workflows/docs.yml`

Pull Request 只构建文档站，不发布。推送到 `main` 后，工作流会把 `docs/.vitepress/dist` 发布到 `gh-pages`。

## PyPI 发布

PaperSeek 的 Python 包通过 `.github/workflows/publish-pypi.yml` 发布到 PyPI。该工作流会：

1. 在 Python 3.12 上构建 wheel 和 sdist。
2. 使用 `twine check` 校验发布产物。
3. 通过 `pypa/gh-action-pypi-publish` 上传到 PyPI。

触发方式：

- 发布 GitHub Release 时自动触发。
- 在 GitHub Actions 页面手动运行 `Publish Python package to PyPI`。

仓库需要配置 secret：

```text
PYPI_API_TOKEN
```

该值应使用 PyPI project-scoped API token，格式通常以 `pypi-` 开头。不要把 PyPI token 写入 `.env.example`、README、文档或 issue。

发布前需要先更新：

- `pyproject.toml` 中的 `project.version`
- `paperseek/__init__.py` 中的 `__version__`

PyPI 不允许覆盖同一版本号。若上传失败提示文件已存在，应升高版本号后重新构建发布。

## gh-pages 分支约束

`gh-pages` 分支应满足：

- 只存静态发布产物。
- 根目录包含生成分支说明 `README.md`。
- 不发 Python 包，不运行 Python 发布流程。
- 不保存任何 secret、token、API Key 或本地配置。
- 默认不接受人工 PR，除非需要紧急修复发布产物。

如果仓库启用了分支保护，需要允许 `github-actions[bot]` 或 GitHub Actions 使用 `GITHUB_TOKEN` 写入 `gh-pages`，否则自动部署会被规则拦截。

## 本地预览

安装依赖：

```bash
npm install
```

启动本地文档站：

```bash
npm run docs:dev
```

构建静态站点：

```bash
npm run docs:build
```
