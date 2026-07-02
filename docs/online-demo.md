# PaperSeek 在线体验版使用说明

PaperSeek 在线体验版用于快速试用完整 Web UI，不需要自己部署服务。页面支持 `EN` / `中文` 语言切换，选择会保存在当前浏览器。

在线体验：

```text
https://www.paperseek.xyz/
```

在线版与开源自托管版共享主要检索核心，但账户、云端历史、站点内置 Key 和配额管理只属于在线版。

## 三种使用模式

在线版配置区提供三个互斥模式，展开一个栏目时会折叠另外两个栏目。

### Quick Start

`Quick Start` 是注册用户的快速试用模式。用户登录后即可使用，不需要自己填写模型 Key 或 OpenAlex Key。

- 需要登录 PaperSeek 在线账号。
- Quick Start 需要已验证邮箱的 PaperSeek 账号；GitHub 或 ModelScope 登录只有在已绑定/合并到已验证邮箱账号后才能使用。
- 默认每日免费额度为 20 次成功检索；只有成功完成的检索计入次数，失败不扣次数。
- 模型 API 和 OpenAlex Key 由 PaperSeek 服务端环境变量提供，不暴露给浏览器。
- 管理员可以在后台为特定用户配置更高的每日额度或临时额度。
- Quick Start 当前使用中国科技云提供的大语言模型接口服务支持。该 API 服务不做 SLA 保证，如遇 `501` 等临时错误，请稍后重试。

### ModelScope Service

`ModelScope Service` 使用登录用户自己的 ModelScope API-Inference 授权调用模型，PaperSeek 仍默认使用站点 OpenAlex key 池。

- 必须通过 ModelScope 登录，或在已登录账号中连接 ModelScope 身份。
- PaperSeek 使用当前会话中的 ModelScope provider token 发起 API-Inference 请求。
- 这里的 API-Inference 也就是 ModelScope 文档中的 API Inference 服务。
- PaperSeek 不会把 ModelScope API-Inference token 保存到数据库。
- 模型调用消耗登录用户自己的 ModelScope API-Inference 免费额度。
- 预重排阶段使用同一个 ModelScope provider token 调用 `Qwen/Qwen3-Embedding-8B`，失败时回退到 `Qwen/Qwen3-Embedding-4B`；外部 reranker 默认关闭，本地 RRF/BM25/embedding 仍会生效。
- ModelScope 模型路由默认是 `Automatic`，会在一组已测试的 API-Inference 模型之间自动尝试；也可以选择 `Custom model` 并填写自定义 ModelScope model ID。
- 使用前请确认 ModelScope 账号已绑定阿里云账号并完成实名认证。API-Inference 可用额度、并发和模型可用性以 ModelScope 实际接口为准。

在线版 ModelScope OAuth 默认使用 `openid profile`。不要额外添加 `email`、`api-inference` 或未在魔搭 OAuth 应用中启用的 scope，否则可能出现 `invalid_scope`。ModelScope Service 的 API-Inference 授权由当前登录会话提供，若授权失效，请退出并重新使用 ModelScope 登录。

### Use your own API

`Use your own API` 适合已有模型服务 API Key 的用户。

- 未登录用户也可以使用。
- 默认 provider 是 `OpenAI`，也可以选择 DeepSeek、中国科技云、ModelScope API-Inference、Ollama 或自定义 OpenAI-compatible 服务。
- API Key、Base URL、模型和运行参数只用于当前浏览器会话。
- 未登录用户使用 OpenAlex 检索时必须填写自己的 OpenAlex Key；登录用户默认可使用站点 OpenAlex key 池，也可在高级设置中覆盖为自己的 Key。
- 自带 API 模式不使用 Quick Start 免费额度，也不消耗 ModelScope Service 的 OAuth token。
- 未登录用户不能使用云端历史记录。

## 账号系统

在线版使用 Supabase Auth 管理账号和云端历史。登录方式包括：

| 登录方式 | 用途 |
| --- | --- |
| 邮箱密码 | 默认账号入口，可用于 Quick Start 和云端 History。 |
| GitHub | 社交登录；如果与已有邮箱账号匹配，会归入同一 Supabase 用户；否则可在账户面板设置密码补充邮箱密码登录。 |
| ModelScope | 社交登录，同时为 ModelScope Service 提供 API-Inference provider token。 |

账户面板会显示当前账号的一览表，包括邮箱密码账号、GitHub 登录、ModelScope 登录、ModelScope API-Inference 授权和 Quick Start 权限。

几个重要规则：

- Quick Start 需要已验证邮箱账号。仅 GitHub 或仅 ModelScope 的 OAuth 登录态在完成邮箱绑定/合并前不能使用 Quick Start。
- 云端 History 只对登录用户可用，并按 Supabase 用户隔离。
- ModelScope Service 必须有 ModelScope provider token；仅邮箱或 GitHub 登录不能代表用户调用 ModelScope API-Inference。
- 如果 OAuth 账号没有对应的邮箱密码登录，账户面板会提示设置密码。这个操作是在当前登录用户上添加邮箱密码登录，不是重新创建另一个账号。
- 公共电脑或共享浏览器使用后请退出登录。

## 推荐流程

1. 进入 [paperseek.xyz](https://www.paperseek.xyz/)。
2. 如需中文界面，点击顶部状态条中的 `中文`。
3. 选择使用模式：
   - 想最快试用：登录后选择 `Quick Start`。
   - 想使用自己的 ModelScope API-Inference 免费额度：选择 `ModelScope Service` 并使用 ModelScope 登录。
   - 想使用自己的模型服务或本地 Ollama：选择 `Use your own API`。
4. 输入 Research Question。
5. 可选：在 Research Question 下方选择数据源和 Source Filter。OpenAlex、WoS、arXiv 使用各自可靠的原生过滤；其它数据源显示 `Field/context hint` 文本提示。
6. 保持默认 OpenAlex 数据源，或在 Research Question 下方切换到 arXiv、Semantic Scholar、PubMed、计算机顶会、Crossref；自带 API 模式还可配置 Web of Science Starter。
7. 点击 `Check Config` 检查配置。失败时页面会弹出问题列表，并提示需要修复的字段。
8. 点击 `Run Search` 开始检索。
9. 在工作流 03 阶段查看候选准备、多路召回、embedding 相似度、RRF 融合、LLM 批量打分、引用扩展重排和摘要补全等子步骤进度。
10. 在 `Results` 查看、筛选和勾选论文，并导出 CSV。
11. 在 `Citation Map` 查看 OpenAlex 引用扩展形成的引用关系图。
12. 登录用户可在 `History` 回看云端历史检索记录。

`TARGET_MAX` 用于指导检索式收窄或放宽，不是最终展示硬上限。在线版默认最多把 256 条预重排候选交给 LLM 打分；最终结果少于 50 条时全部展示，结果较多时至少展示前 50 条，如果 5 分及以上候选超过 50 条，则展示全部高分候选。

## Discipline Fields

在线体验版与开源自托管版使用同一套 Source Filter 逻辑。它会随所选数据源切换：OpenAlex 使用 OpenAlex Field，WoS Starter 使用 Web of Science Category，arXiv 使用 arXiv Category；没有可靠硬过滤的数据源显示 `Field/context hint`。

不同数据源的处理方式不同：

| 数据源 | 在线版处理方式 |
| --- | --- |
| OpenAlex | 应用 `primary_topic.field.id` 原生过滤，并把所选学科传给引用扩展。 |
| Web of Science Starter | Web of Science Category 仅作为构建 `TS` / `TI` / `SO` 检索式的上下文；Starter API 当前不接受 `WC=`。 |
| arXiv | 应用 arXiv Category 的 `cat:` 限制。 |
| Semantic Scholar、PubMed、Crossref、计算机顶会 | 没有可靠硬学科过滤时，PaperSeek 使用 `Field/context hint` 辅助 LLM 构建检索式。 |

`Field/context hint` 是自由文本提示，用来帮助 LLM 生成更贴近领域的检索式；Source Filter 是结构化源端限制，更适合在结果过宽时收窄候选池。

## 权限对照

| 功能 | 未登录 | 邮箱/GitHub 登录 | ModelScope 登录或已连接 ModelScope |
| --- | --- | --- | --- |
| Use your own API | 支持，需要自填模型 Key；OpenAlex 需自填 Key | 支持，可默认使用站点 OpenAlex key 池 | 支持，可默认使用站点 OpenAlex key 池 |
| Quick Start | 不支持 | 支持，每日成功检索额度 | 支持，每日成功检索额度 |
| ModelScope Service | 不支持 | 不支持，除非连接 ModelScope | 支持，使用当前账号 API-Inference 授权 |
| 云端 History | 不支持 | 支持 | 支持 |

公共电脑或共享浏览器使用后请退出登录。历史记录按登录账号隔离，不按 IP 地址隔离。

## 使用前检查

使用 `ModelScope Service` 前，请确认：

- ModelScope 账号已经绑定阿里云账号。
- 绑定的阿里云账号已完成实名认证。
- 如果使用 RAM 账号，需要按官方教程完成对应的绑定与授权。
- 授权登录 PaperSeek 后保持当前 ModelScope 会话有效；如果模型调用提示授权失败，请退出并重新使用 ModelScope 登录。

如果登录成功但模型调用失败，请先检查 ModelScope 账号的阿里云绑定、实名认证和授权状态。完成绑定或授权后，建议退出 PaperSeek 并重新登录一次。

ModelScope API-Inference 的官方限制请以文档为准：

- [API-Inference 使用限制](https://modelscope.cn/docs/model-service/API-Inference/limits)
- [阿里云账号绑定与授权教程](https://modelscope.cn/docs/accounts/aliyun-binding-and-authorization)

## API-Inference 稳定性与额度

ModelScope API-Inference 是面向开发者的免费体验能力，不是商业 SLA 服务。它可能受到用户总额度、单模型额度、动态并发限制和平台资源压力影响：

- 每位 ModelScope 注册用户通常有每日总调用额度。
- 每个模型还有独立的单模型每日额度，额度会随资源和使用情况动态调整。
- 如果某个模型返回空响应、`429` 或额度不足，在线版会尽量通过自动路由尝试其它可用模型。
- 仍失败时可稍后重试，或改用 `Quick Start` / `Use your own API`。
- PaperSeek 会读取 ModelScope 响应头中的额度信息，并在日志里显示用户总额度和当前模型额度的剩余情况。

## 历史记录

在线版会为登录用户保存：

- 检索问题和运行配置摘要。
- 工作流日志事件。
- 数据源返回的候选论文。
- 最终排序结果。

历史记录按登录账号隔离。不同浏览器、设备或网络环境中，只要登录同一个账号，就能看到同一账号的历史记录；不同账号之间不会共享历史记录。历史记录不会保存用户输入的模型 API Key、OpenAlex Key 或 ModelScope provider token。

## 与开源自托管版的区别

| 项目 | 在线体验版 | 开源自托管版 |
| --- | --- | --- |
| 登录 | 使用 Supabase 账号系统；Quick Start 和 History 需要登录 | 默认不需要登录 |
| 模型调用 | Quick Start 可使用站点免费额度；ModelScope Service 使用用户 OAuth 授权；也可自带 API | 使用你自己配置的 LLM API Key |
| OpenAlex Key | 登录用户默认使用站点 key 池；未登录自带 API 模式需自填 OpenAlex Key | 可匿名访问或自己配置 key |
| Discipline Fields | 页面选择，随本次搜索提交 | 页面选择、CLI 参数或 `DISCIPLINE_FIELDS` 环境变量 |
| 历史记录 | 登录后保存到云端 Supabase 数据库 | 默认保存到本地 SQLite |
| 适用场景 | 快速体验、轻量检索、临时试用 | 私有部署、长期使用、可控配置 |

## 隐私提示

不要在研究问题中输入不应上传到第三方模型服务的敏感内容。在线版会把检索问题、候选论文元数据和排序提示发送给当前模式选择的模型服务，以完成检索式生成和结果排序。

如果需要长期使用、私有部署、稳定额度或完全控制 API Key 与数据存储，请使用开源自托管版，并配置自己的模型服务和数据源。

## English

The hosted PaperSeek edition lets users try the full Web UI without deploying their own server. It shares the main search core with the open-source edition, while account handling, hosted history, site-provided keys, and quota management belong to the hosted service.

Hosted URL:

```text
https://www.paperseek.xyz/
```

The hosted configuration panel has three mutually exclusive modes:

- `Quick Start`: requires sign-in. PaperSeek provides the model key and OpenAlex key pool. The default quota is 20 successful searches per day, and failed searches do not consume quota. The Quick Start model API is provided through CSTCloud and has no SLA guarantee.
- `ModelScope Service`: requires ModelScope sign-in or a connected ModelScope identity. Model calls use the signed-in user's ModelScope API-Inference provider token, while OpenAlex uses the hosted key pool by default. Embedding pre-ranking uses the same provider token with `Qwen/Qwen3-Embedding-8B` and fallback `Qwen/Qwen3-Embedding-4B`; external rerank is off by default. Model routing defaults to Automatic with a tested fallback pool.
- `Use your own API`: can be used without sign-in. Users provide their own model API key and, when anonymous, their own OpenAlex key for OpenAlex searches. Signed-in users may use the hosted OpenAlex key pool unless they override it.

All modes support the same source-specific filter behavior as the open-source Web UI. Leave it at `Any filter` for broad discovery. OpenAlex applies native `primary_topic.field.id`, arXiv applies `cat:`, and WoS Starter uses selected Web of Science Categories only as query-building context because the Starter API currently rejects `WC=`. Sources without reliable native discipline filtering use `Field/context hint` only as LLM query context.

Accounts are managed through Supabase Auth. Email/password is the default account entry; GitHub and ModelScope are OAuth identities on the same user model. Quick Start requires a verified-email PaperSeek account, while GitHub or ModelScope sign-in can use Quick Start only after the identity is linked or merged into a verified-email account. Hosted History is available to signed-in users. ModelScope Service specifically requires a ModelScope provider token in the current session.

The hosted ModelScope OAuth flow uses `openid profile` by default. Adding unsupported scopes such as `email` or `api-inference` can cause `invalid_scope`; if ModelScope Service later reports authorization failure, sign out and sign in with ModelScope again.

`TARGET_MAX` guides query narrowing rather than final display. Hosted scoring defaults to at most 256 pre-ranked candidates; results show all records when fewer than 50 are scored, otherwise at least the top 50 and all candidates scoring `5` or above when that high-score set is larger. Stage 03 in the Web UI shows progress for candidate preparation, multi-lane retrieval, embedding similarity, RRF fusion, LLM ranking batches, citation-expansion reranking, and abstract enrichment.

Hosted history is isolated by authenticated user and does not store raw user model keys, OpenAlex keys, or ModelScope provider tokens. Sign out after using PaperSeek on a shared computer.
