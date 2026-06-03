# PaperSeek 在线体验版使用说明

PaperSeek 在线体验版用于快速试用完整 Web UI，不需要自己部署服务，也不需要准备 OpenAlex Key。

在线体验：

```text
https://www.paperseek.xyz/
```

## 使用流程

1. 点击页面右上角登录按钮。
2. 使用 ModelScope 账号授权登录。
3. 在 `Quick Start` 中输入研究问题，选择数据源和模型。
4. 点击 `Run Search` 开始检索。
5. 在 `Results` 查看、筛选和勾选论文，并导出 CSV。
6. 在 `Citation Map` 查看引用关系图。
7. 在 `History` 回看已登录账号的历史检索记录。

## 账号与额度

在线体验版使用 ModelScope OAuth 登录。登录后：

- PaperSeek 使用登录用户授权的 ModelScope API Inference token 调用模型。
- 模型调用消耗登录用户自己的 ModelScope API Inference 免费额度。
- PaperSeek 不会把 ModelScope API Inference token 保存到数据库；token 只随当前登录会话用于发起模型请求。
- 历史记录按登录账号隔离，不按 IP 地址隔离。公共电脑或共享浏览器使用后请退出登录。

ModelScope API Inference 的官方限制请以文档为准：

- [API-Inference 使用限制](https://modelscope.cn/docs/model-service/API-Inference/limits)
- [阿里云账号绑定与授权教程](https://modelscope.cn/docs/accounts/aliyun-binding-and-authorization)

## 使用前检查

ModelScope API Inference 不是商业 SLA 服务，而是面向开发者的免费体验能力。使用在线体验版前，请确认：

- ModelScope 账号已经绑定阿里云账号。
- 绑定的阿里云账号已完成实名认证。
- 如果使用 RAM 账号，需要按官方教程完成对应的绑定与授权。
- 授权登录 PaperSeek 时允许 `api-inference` 范围，否则无法代表当前用户调用模型。

如果登录成功但模型调用失败，请先检查 ModelScope 账号的阿里云绑定、实名认证和授权状态。完成绑定或授权后，建议退出 PaperSeek 并重新登录一次。

## API Inference 额度规则

根据 ModelScope 官方说明，API Inference 会受到用户总额度、单模型额度和动态并发限制的共同约束：

- 每位 ModelScope 注册用户当前每天有一个总调用额度，官方文档示例为所有模型合计每天 2000 次。
- 每个模型还有独立的单模型每日额度，额度会随资源和使用情况动态调整，最高不超过 200 次，也可能远低于 200 次。
- 如果某个模型返回 `429` 或额度不足，可以切换其他模型，或等到第二天额度重置后再试。
- 平台会根据实时资源压力动态调整并发和速率限制，在线体验版更适合单人、低并发、轻量检索。
- 较早模型可能会逐步降低额度或下架，模型列表和可用额度以 ModelScope 实际页面和接口返回为准。

PaperSeek 会读取 ModelScope 响应头中的额度信息，并在日志里显示用户总额度和当前模型额度的剩余情况。ModelScope 文档列出的相关响应头包括：

| 响应头 | 含义 |
| --- | --- |
| `modelscope-ratelimit-requests-limit` | 用户当天总额度 |
| `modelscope-ratelimit-requests-remaining` | 用户当天剩余额度 |
| `modelscope-ratelimit-model-requests-limit` | 当前模型当天额度 |
| `modelscope-ratelimit-model-requests-remaining` | 当前模型当天剩余额度 |

## 适用边界

在线体验版适合快速试用、轻量检索和查看 PaperSeek 的完整 Web UI。它不适合高并发、批量自动化、商业生产任务，或需要稳定 SLA 的场景。

如果需要长期使用、私有部署、稳定额度或完全控制 API Key 与数据存储，请使用开源自托管版本，并配置自己的模型服务和数据源。

## 历史记录

在线体验版会保存当前登录账号的检索历史，包括：

- 检索问题和运行配置。
- 工作流日志。
- 数据源返回的候选论文。
- 最终排序结果。

历史记录按登录账号隔离。不同浏览器、不同设备或不同网络环境中，只要登录的是同一个账号，就能看到同一账号的历史记录；不同账号之间不会共享历史记录。

## 与开源自托管版的区别

| 项目 | 在线体验版 | 开源自托管版 |
| --- | --- | --- |
| 登录 | 需要 ModelScope 登录 | 默认不需要登录 |
| 模型额度 | 使用登录用户的 ModelScope API Inference 额度 | 使用你自己配置的 LLM API Key |
| OpenAlex Key | 使用站点服务端 key 池 | 可匿名访问或自己配置 key |
| 历史记录 | 保存到托管服务的数据库 | 默认保存到本地 SQLite |
| 适用场景 | 快速体验、轻量检索 | 私有部署、长期使用、可控配置 |

## 隐私提示

不要在研究问题中输入不应上传到第三方模型服务的敏感内容。在线体验版会把检索问题、候选论文元数据和排序提示发送给配置的模型服务，以完成检索式生成和结果排序。

## English

The hosted PaperSeek demo lets you try the full Web UI without deploying your own server or preparing an OpenAlex key.

URL:

```text
https://www.paperseek.xyz/
```

Sign in with a ModelScope account. Model calls use the signed-in user's ModelScope API Inference quota, and search history is stored by the hosted service. PaperSeek does not store the ModelScope API Inference token in the database; it is used only for the current authenticated session.

Before using API Inference, make sure the ModelScope account is linked to an Alibaba Cloud account, has completed real-name verification, and has granted the `api-inference` OAuth scope. For RAM accounts, follow the official binding and authorization guide.

Official ModelScope references:

- [API Inference usage limits](https://modelscope.cn/docs/model-service/API-Inference/limits)
- [Alibaba Cloud account binding and authorization](https://modelscope.cn/docs/accounts/aliyun-binding-and-authorization)

According to the official usage-limit documentation, API Inference is a free developer-oriented service rather than a production SLA service. It is subject to a daily per-user quota, a separate per-model daily quota, and dynamic rate limits. If a request returns `429` or a quota error, switch to another available model or retry after the quota resets.

PaperSeek reads ModelScope quota headers when available and shows remaining user/model quota in the run log.

History is isolated by the authenticated account, not by IP address. Sign out after using PaperSeek on a shared computer. For private deployment, long-term use, or full control over API keys and storage, use the open-source self-hosted version instead.
