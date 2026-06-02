# PaperSeek Agent Skills

本目录存放 PaperSeek 随项目发布的 agent skill。它不是 Python 包源码，也不保存任何 API Key、cookie 或账号信息。

## 目录结构

```text
skills/
├── README.md
└── paperseek/
    ├── SKILL.md
    └── references/
        ├── cli-contract.md
        ├── management-layer.md
        └── source-routing.md
```

`skills/paperseek/` 是真正的 Skill 文件夹。它采用 progressive disclosure：

- `SKILL.md`：短指令、触发条件、核心工作流。
- `references/`：只有在需要时才读取的命令契约、数据源选择和诊断说明。

## 用途

这个 Skill 用来指导 AI agent 正确调用 PaperSeek：

- 用自然语言研究问题运行文献检索。
- 在 OpenAlex、Crossref、WoS Starter 之间选择合适数据源。
- 运行 `doctor` 和 `smoke` 排查配置、网络和数据源问题。
- 读取 JSON 输出和稳定结果字段。
- 明确不做 PDF 下载、不绕过付费墙、不保存密钥。

`skills/paperseek/scripts/paperseek.py` 是一个完整包启动器，而不是最小降级版 CLI。它会调用完整的 `paperseek` Python 包；如果包没有安装，会给出安装指引。这样 Skill 可以单独发布并保留稳定 script 入口，同时避免维护两套检索实现。

## 安装思路

如果你的 agent 平台支持本地 Skill 文件夹，可以把 `skills/paperseek/` 复制或链接到对应的 Skill 目录。不同平台的安装目录不同；以平台文档为准。

在本项目源码目录中测试 PaperSeek CLI：

```powershell
pip install -e .
paperseek doctor
paperseek smoke --source openalex --query "machine learning"
python .\skills\paperseek\scripts\paperseek.py doctor
```

API Key 应通过环境变量、`paperseek config set ...` 或 Web UI 本次会话配置。不要把真实 key 写入 `skills/` 目录。
