# PaperSeek 在线体验版使用说明

在线体验版用于直接试用完整 Web UI，不需要自己部署服务。它与开源自托管版共享主要检索核心，但账号、云端历史、站点 Key 池和额度管理只属于在线版。

在线体验地址：

```text
https://www.paperseek.xyz/
```

## 三种使用模式

配置区提供三个互斥模式，展开一个栏目时会折叠另外两个栏目。

### PaperSeek Service

`PaperSeek Service` 是注册用户的轻量试用模式。用户登录并完成邮箱验证后即可使用，不需要自己填写模型 Key 或已纳入服务范围的数据源 Key。

- 默认每日额度为 20 次成功检索；失败不消耗额度。
- 当前支持 OpenAlex、arXiv、Semantic Scholar、PubMed 和计算机顶会检索。
- OpenAlex 使用站点 OpenAlex key 池；Semantic Scholar 和 PubMed 在服务端配置了对应 Key 时使用站点 Key。
- `Auto` 模式会自动选择当前最合适的模型，默认使用本地 hashing sparse cosine 和 RRF 预重排。
- `Custom` 模式允许用户选择站点提供的请求模型、Embedding 模型和预重排方式；前端只显示模型名，后端负责映射到对应服务商。
- 免费模型仅面向个人注册用户提供轻量使用支持。PaperSeek 是个人维护的开源项目，免费额度有限且不做 SLA 稳定性保证；重度使用请部署开源版并填写自己的 API key。
- 个人用户需要提高额度时，请提供姓名、单位、用途和 UID（右上角账户信息页的 Signed-in account 栏目）发送至 `paperseek-community@outlook.com`。

### Third-party Service

`Third-party Service` 使用用户自己的第三方推理额度，当前支持 ModelScope、OpenRouter 和 Hugging Face。

- ModelScope：必须通过 ModelScope 登录，或在已登录账号中连接 ModelScope 身份。ModelScope 官方文档也会写作 API Inference；本文中的 API-Inference 与 API Inference 指同一服务。PaperSeek 使用当前会话中的 ModelScope provider token 发起请求，不会保存该 token。使用前请确认 ModelScope 账号已绑定阿里云账号并完成实名认证。在线版 ModelScope OAuth 默认使用 `openid profile`，不要额外添加 `email`、`api-inference` 或未在魔搭 OAuth 应用中启用的 scope，否则可能出现 `invalid_scope`。
- OpenRouter：点击授权后使用浏览器中的 OpenRouter PKCE 会话，不走 Supabase OAuth。`Free Model Automatic` 会拉取当前可用的免费模型，并按 OpenRouter 模型元数据优先选择 text 能力模型；也可以填写自定义模型。
- Hugging Face：通过 Supabase custom OAuth/OIDC 连接 Hugging Face，scope 包含 `openid profile email inference-api`。PaperSeek 使用 Hugging Face Router 的 OpenAI-compatible endpoint `https://router.huggingface.co/v1` 代表用户发起推理请求。
- ModelScope 的 Embedding 预重排使用同一 provider token 调用 `Qwen/Qwen3-Embedding-8B`，失败时回退到 `Qwen/Qwen3-Embedding-4B`。OpenRouter 和 Hugging Face 的 Automatic 模式只使用可明确识别的免费模型；如果没有可用的免费 embedding 或 rerank 模型，会回退到本地 hashing embedding、BM25 和 RRF。
- 第三方服务的可用额度、并发和模型可用性以对应平台实际接口为准。

### Bring your own Key

`Bring your own Key` 适合已有模型服务 API Key 的用户，也可以理解为 bring your own provider keys (BYOK) 模式。

- 未登录用户也可以使用。
- 默认 provider 是 OpenAI，也可以选择 DeepSeek、中国科技云、ModelScope API-Inference、Ollama、OpenRouter、NVIDIA NIM 或自定义 OpenAI-compatible 服务。
- API Key、Base URL、模型和运行参数只用于当前浏览器会话。
- 未登录用户使用 OpenAlex 检索时必须填写自己的 OpenAlex Key；登录用户默认可使用站点 OpenAlex key 池，也可在高级设置中覆盖为自己的 Key。
- BYOK 模式不使用 PaperSeek Service 免费额度，也不消耗 Third-party Service 的 OAuth/session token。
- 未登录用户不能使用云端历史记录。

## 账号和权限

在线版使用 Supabase Auth 管理账号和云端历史。登录方式包括邮箱、GitHub、ModelScope 和 Hugging Face。GitHub、ModelScope 与 Hugging Face 是同一账号模型下的 OAuth 身份；PaperSeek Service 需要已验证邮箱的 PaperSeek 账号。OpenRouter 授权保存在当前浏览器会话中，不作为 Supabase 登录身份。

账户面板会显示当前账号的一览表，包括邮箱账号、GitHub 登录、ModelScope 登录、Hugging Face 登录、第三方推理授权和 PaperSeek Service 权限。

| 功能 | 未登录 | 邮箱/GitHub 登录 | 已连接 ModelScope 或 Hugging Face | OpenRouter 已授权 |
| --- | --- | --- | --- | --- |
| Bring your own Key | 支持，需要自填模型 Key；OpenAlex 需自填 Key | 支持，可默认使用站点 OpenAlex key 池 | 支持，可默认使用站点 OpenAlex key 池 | 支持；OpenRouter 仅用于本次浏览器会话 |
| PaperSeek Service | 不支持 | 支持，每日成功检索额度 | 支持，每日成功检索额度 | 不支持，除非同时登录 PaperSeek 账号 |
| Third-party Service | OpenRouter 授权后可使用 OpenRouter | 连接对应第三方后可使用 | 支持对应平台授权 | 支持 OpenRouter 会话授权 |
| 云端 History | 不支持 | 支持 | 支持 | 不支持，除非同时登录 PaperSeek 账号 |

公共电脑或共享浏览器使用后请退出登录。历史记录按登录账号隔离，不按 IP 地址隔离。

## 推荐流程

1. 进入 [paperseek.xyz](https://www.paperseek.xyz/)。
2. 如需中文界面，点击顶部状态栏中的 `中文`。
3. 选择使用模式：
   - 想快速试用：登录后选择 `PaperSeek Service`。
   - 想使用自己的 ModelScope、OpenRouter 或 Hugging Face 推理额度：选择 `Third-party Service` 并连接对应服务。
   - 想使用自己的模型服务、本地 Ollama 或完整数据源能力：选择 `Bring your own Key`。
4. 输入 Research Question。
5. 在 Research Question 下方选择数据源和 Source Filter。OpenAlex、WoS、arXiv 使用各自可靠的原生过滤；其他数据源显示 `Field/context hint` 文本提示。
6. 点击 `Check Config` 检查配置。失败时页面会弹出问题列表，并提示需要修复的字段。
7. 点击 `Run Search` 开始检索。
8. 在工作流 03 阶段查看候选准备、多路召回、Embedding 相似度、RRF 融合、LLM 批量打分、引用扩展重排和摘要补全等子步骤进度。
9. 在 `Results` 查看、筛选和勾选论文，并导出 CSV。
10. 在 `Citation Map` 查看 OpenAlex 引用扩展形成的引用关系图。
11. 登录用户可在 `History` 回看云端历史检索记录。

`TARGET_MAX` 用于指导检索式收窄或放宽，不是最终展示硬上限。在线版默认最多把 256 条预重排候选交给 LLM 打分；最终结果少于 50 条时全部展示，结果较多时至少展示前 50 条，如果 5 分及以上候选超过 50 条，则展示全部高分候选。

## 与开源自托管版的区别

| 项目 | 在线体验版 | 开源自托管版 |
| --- | --- | --- |
| 登录 | 使用 Supabase 账号系统；PaperSeek Service 和 History 需要登录 | 默认不需要登录 |
| 模型调用 | PaperSeek Service 可使用站点免费额度；Third-party Service 使用用户第三方授权；也可 BYOK | 使用你自己配置的 LLM API Key |
| OpenAlex Key | 登录用户默认使用站点 key 池；未登录 BYOK 模式需自填 OpenAlex Key | 可匿名访问或自己配置 key |
| Source Filter | 页面选择，随本次搜索提交 | 页面选择、CLI 参数或 `DISCIPLINE_FIELDS` 环境变量 |
| 历史记录 | 登录后保存到云端 Supabase 数据库 | 默认保存到本地 SQLite |
| 适用场景 | 快速体验、轻量检索、临时试用 | 私有部署、长期使用、可控配置 |

## English Summary

The hosted PaperSeek edition lets users try the full Web UI without deploying their own server. It shares the main search core with the open-source edition, while account handling, hosted history, site-provided keys, and quota management belong to the hosted service.

The hosted configuration panel has three mutually exclusive modes:

- `PaperSeek Service`: requires sign-in and a verified email. PaperSeek provides hosted model routes plus server-side source keys for OpenAlex, Semantic Scholar, and PubMed where configured. It currently exposes OpenAlex, arXiv, Semantic Scholar, PubMed, and computer science top-conference search. The default quota is 20 successful searches per day; failed searches do not consume quota. Auto mode keeps embedding local and pre-ranking on RRF, while Custom mode lets users choose hosted request, embedding, and rerank models.
- `Third-party Service`: uses the user's own third-party inference quota. ModelScope uses the signed-in user's API-Inference provider token; OpenRouter uses a browser PKCE session and can automatically try current free text models; Hugging Face uses Supabase custom OAuth/OIDC with the `inference-api` scope and the OpenAI-compatible Router endpoint. Automatic embedding/rerank only uses clearly identifiable free models and otherwise falls back to local hashing, BM25, and RRF.
- `Bring your own Key`: can be used without sign-in. Users follow the bring your own provider keys (BYOK) pattern, including their own model API key and, when anonymous, their own OpenAlex key for OpenAlex searches.

Hosted history is isolated by authenticated user and does not store raw user model keys, OpenAlex keys, ModelScope provider tokens, OpenRouter session keys, or Hugging Face provider tokens. Sign out after using PaperSeek on a shared computer.
