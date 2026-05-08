# Bedrock API 调试工具包

> 面向首次接入 AWS Bedrock 的客户，提供一套**可直接运行**的调试脚本。
> 覆盖：基础 Converse、流式输出、Tool Use、环境诊断。
> Region 建议：`us-east-1` 或 `us-west-2`（都是 Bedrock 主力 region，Opus 4.6 两个都支持）
> 默认模型：`us.anthropic.claude-opus-4-6-v1`（Claude Opus 4.6，2026-02 发布）

---

## 快速开始

```bash
cd aws-best-practices-cn/bedrock-debug

# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 AWS 凭证（三选一）

# 方式 A：IAM access key（两个必须一起，单独 SECRET 不行）
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=wJalrXUtn...
# 临时凭证还需要：export AWS_SESSION_TOKEN=...

# 方式 B：AWS Profile（推荐本地开发）
aws configure --profile bedrock-dev
export AWS_PROFILE=bedrock-dev

# 方式 C：Bedrock 专用 API Key（2025 新增，只要一个变量）
# 在 Bedrock console → API keys 生成
export AWS_BEARER_TOKEN_BEDROCK="bedrock-api-key-..."

# 3. 先跑环境诊断，确认权限和模型访问
python 00_diagnose.py

# 4. 按顺序验证
python 01_basic_converse.py
python 02_streaming.py
python 03_tool_use.py
```

> 💡 **常见误区**：只设 `AWS_SECRET_ACCESS_KEY` 不行，它必须和 `AWS_ACCESS_KEY_ID` 成对使用。
> 想只用一个环境变量就跑通，请用方式 C（Bedrock API Key）。

---

## 脚本说明

| 脚本 | 场景 | 对应文档章节 |
|---|---|---|
| `00_diagnose.py` | 环境诊断：凭证、region、模型访问权限 | — |
| `01_basic_converse.py` | 基础 Converse API 调用 + 用量统计 | §1 基础调用 |
| `02_streaming.py` | `converse_stream` 流式输出 | §2 流式输出 |
| `03_tool_use.py` | Tool Use 完整两轮对话（模型→工具→回填→最终回答） | §3 Function Calling |

---

## 原理速览：三种调用模式的本质区别

三个脚本本质上是同一套 Converse API 的三种用法，差别在**要不要边生成边返回** + **模型能不能调外部工具**。

### 共同底座：Converse API

所有脚本都走 `bedrock-runtime` 的 `Converse` / `ConverseStream`，核心数据结构长一个样：

```python
{
  "modelId": "us.anthropic.claude-opus-4-6-v1",
  "system":   [...],           # 系统提示（可选）
  "messages": [                # 多轮对话历史
    {"role": "user/assistant", "content": [<block>, <block>, ...]}
  ],
  "inferenceConfig": {...},    # maxTokens / temperature 等
  "toolConfig": {...}          # 仅 Tool Use 需要
}
```

**为什么不用老的 `InvokeModel`**：InvokeModel 每个模型的 body 格式都不一样（Claude 一套、Nova 一套、Llama 一套），换模型要改代码。Converse 是 AWS 抽象出的**统一协议**，换 `modelId` 其余不动。

**关键设计：`content` 是数组不是字符串**。每个 block 可以是 `text`、`image`、`document`、`toolUse`、`toolResult` 等。同一个 API 能支持多模态和 function calling，就是靠 block 类型扩展出来的。

---

### 01 Basic Converse — 请求 / 响应

```
你 ──(HTTP POST)──▶ Bedrock ──▶ 模型生成完整回答 ──▶ 一次返回
```

最简单的同步调用：发一个 request，**等模型把整段话生成完**再一次性返回。

**要点**：
- 底层是 HTTPS 同步调用，模型生成多久你就阻塞多久
- 响应里拿两样东西：`output.message.content[0].text`（回答）+ `usage`（token 数，算钱和观测用）
- `stopReason` 告诉你为什么停：`end_turn`（正常）、`max_tokens`（被截断）、`tool_use`（要调工具）、`guardrail_intervened`（被 Guardrail 拦了）

**适用**：短回答、后台批处理、延迟不敏感。
**不适用**：Lambda（29 秒超时）、前端聊天框（用户看着空白等半天）。

---

### 02 Streaming — 服务端推送（EventStream）

```
你 ──▶ Bedrock ──▶ 模型边生成边切片 ──▶ 事件流
                                      │
                                      ├─ messageStart
                                      ├─ contentBlockDelta {text: "云"}   ← 一个 token
                                      ├─ contentBlockDelta {text: "朵"}
                                      ├─ ...
                                      ├─ messageStop {stopReason}
                                      └─ metadata {usage}
```

**要点**：
- 底层走 HTTP/2 chunked transfer，AWS 封装成 EventStream 二进制协议，boto3 自动解码成 Python 迭代器
- 服务端每生成几个 token 就推一个 `contentBlockDelta` 事件，**不等全部生成完**
- 事件类型：边界标记（`messageStart` / `messageStop`）、内容增量（`contentBlockDelta`）、最终元数据（`metadata`，带 usage）
- **TTFT**（Time To First Token）是核心指标 —— 用户在这之后立刻能看到字，哪怕总耗时 10 秒

**适用**：聊天界面（打字机效果）、长生成（避免 29s 超时）、需要边生成边判断是否中断。
**代价**：代码稍复杂，要处理事件循环；上游链路（API Gateway + Lambda）要支持流式转发，不然优势发挥不出来。

---

### 03 Tool Use — 两次往返 + 本地执行

这是最容易让人困惑的。**模型自己不会调用任何 API** —— 它只会"说"想调什么工具，**真正执行工具的是你的代码**。

```
第 1 轮：
  你 ──▶ Bedrock (prompt + 工具清单)
  模型 ──▶ 你: "我想调 get_weather(city='上海')"
             (stopReason="tool_use", content 里带 toolUse 块)

本地：
  你的 Python 代码执行 get_weather("上海") → {"temp": 22, ...}

第 2 轮：
  你 ──▶ Bedrock (原 messages + assistant 的 toolUse + 新 user 的 toolResult)
  模型 ──▶ 你: "上海今天多云，气温 22°C"
             (stopReason="end_turn")
```

**要点**：

1. **工具只是"描述"**：`toolConfig.tools` 里给的不是代码，是 JSON Schema 描述的函数签名。模型根据描述决定**什么时候调、传什么参数**，但它自己没有执行权。

2. **通过"对话历史"回填结果**：工具结果不是一个特殊字段，而是伪装成一条 `role="user"` 的新消息，内容是 `toolResult` block。模型把它理解成"用户告诉我工具的返回值是这个"，再基于此生成最终回答。

3. **`toolUseId` 是唯一对应关系**：模型一次可能请求多个工具（同时问上海和北京天气 → 两个 `toolUse`），执行完按 id 配对回填，顺序无所谓。

4. **可能多轮迭代**：复杂任务里模型可能连续请求多个工具（查完天气再查航班），每次都走"执行 → 回填 → 再请求"的循环，直到 `stopReason == "end_turn"`。

**本质**：function calling 不是 AI 的新能力，而是**把 LLM 变成一个能输出结构化调用指令的决策器**。你的代码负责执行、沙箱隔离、权限控制。所以安全性完全由你决定 —— 模型永远不直接碰你的数据库。

**适用**：Agent（查日历、发邮件、查数据库）、RAG 的动态检索、需要外部实时数据（汇率、天气、股价）的对话。

---

### 三者对比

| 维度 | 01 Basic | 02 Streaming | 03 Tool Use |
|---|---|---|---|
| API | `converse` | `converse_stream` | `converse`（也可流式） |
| 返回方式 | 一次性 | 事件流 | 一次性（但要多轮往返） |
| 模型扮演的角色 | 回答者 | 回答者 | **决策者**（决定要不要用工具） |
| 代码复杂度 | ⭐ | ⭐⭐ | ⭐⭐⭐ |
| 延迟感知 | 差（等全部） | 好（TTFT 短） | 中（取决于工具） |
| 典型用途 | 后台任务 | 前端聊天 | Agent |

**一句话总结**：01 是"让模型说话"，02 是"让模型边想边说"，03 是"让模型学会喊人帮忙"。组合起来就能搭出 90% 的 LLM 应用。

---

## 常见报错速查

| 报错 | 原因 | 处理 |
|---|---|---|
| `AccessDeniedException: ... don't have access to model` | 模型未在 Bedrock console 申请开通 | Bedrock → Model access → Request access |
| `ValidationException: ... on-demand throughput isn't supported` | 新模型（Opus 4.6 / Sonnet 4.6 等）必须用 **cross-region inference profile** | 把 modelId 换成 `us.anthropic.claude-opus-4-6-v1`（注意前缀 `us.`，且**不带 `:0` 后缀**） |
| `ValidationException: ... invalid model identifier` | 用了 Opus 4.6 的旧格式 `anthropic.claude-opus-4-6-v1:0` | 去掉 `:0` 后缀，新模型 ID 格式是 `anthropic.claude-opus-4-6-v1` |
| `ValidationException: temperature and top_p cannot both be specified` | Opus 4.6 / Sonnet 4.6 新约束：两个采样参数不能共存 | 二选一：要确定性保留 `temperature`，要多样性用 `topP`。老模型的「两个都设」写法在新模型会失败 |
| `ThrottlingException` | 账号配额/突发限流 | 已在脚本里开启 `adaptive` 重试；若持续，申请提 quota |
| `ResourceNotFoundException` | region 错或 modelId 拼错 | 确认 region 在 CRIS profile 支持列表内（us-east-1 / us-west-2 都可），modelId 带区域前缀 |
| `UnrecognizedClientException` | IAM 凭证无效或过期 | `aws sts get-caller-identity` 验证 |
| 超过 29 秒超时 | Lambda/API GW 限制，未用流式 | 改用 `converse_stream`（`02_streaming.py`） |

---

## IAM 最小权限

调用 Bedrock 所需的最小 IAM policy：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:Converse",
        "bedrock:ConverseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/*",
        "arn:aws:bedrock:*:*:inference-profile/*",
        "arn:aws:bedrock:*:*:application-inference-profile/*"
      ]
    }
  ]
}
```

> **注意**：cross-region inference profile 需要 `inference-profile/*` 这条 Resource，
> 否则会报 `not authorized to perform: bedrock:InvokeModel on resource: ...inference-profile/...`。
> 用 `global.` 前缀时建议 `Resource: "*"`，因为请求会路由到任意 region。

---

## 模型 ID 参考（2026-05）

| 模型 | 推荐 Inference Profile ID | 说明 |
|---|---|---|
| **Claude Opus 4.6** ⭐ | `us.anthropic.claude-opus-4-6-v1` | 当前旗舰，1M context / 128K 输出，支持 reasoning |
| Claude Sonnet 4.6 | `us.anthropic.claude-sonnet-4-6` | 中档，1M context，性价比高 |
| Claude Sonnet 4.5 | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | 上一代 Sonnet |
| Claude Haiku 3.5 | `us.anthropic.claude-3-5-haiku-20241022-v1:0` | 低延迟 / 低成本 |
| Nova Pro | `us.amazon.nova-pro-v1:0` | AWS 自家 |

**CRIS 前缀含义**：
- `us.` — 请求路由到美国 region（us-east-1/2、us-west-1/2、ca-central-1、ca-west-1）
- `eu.` — 欧洲 region（Frankfurt、Stockholm、Ireland 等）
- `au.` — 澳洲 region（Sydney、Melbourne）
- `global.` — 全球路由，吞吐最大，**无数据驻留限制时用这个**

> 注意：Opus 4.6 / Sonnet 4.6 的 ID **不再带 `:0` 后缀**，这是新格式。
> 可用 `aws bedrock list-inference-profiles --region us-east-1` 查询当前账号可见的 profile。

---

## 生产建议（节选）

- **观测**：每次响应里的 `usage.inputTokens / outputTokens` 上报到 CloudWatch EMF
- **缓存**：长 system prompt 加 `cachePoint` 节省 token
- **批量**：离线大批量用 Batch Inference，成本省 50%+
- **安全**：调用时加 `guardrailConfig`，启用 Bedrock Guardrails
- **Agent**：多步工具编排用 [Strands Agents](https://github.com/strands-agents/sdk-python) 或 LangChain `ChatBedrockConverse`

---

## 参考资料

- [Converse API 官方文档](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html)
- [Bedrock Workshop](https://github.com/aws-samples/amazon-bedrock-workshop)
- [Bedrock Agent Samples](https://github.com/awslabs/amazon-bedrock-agent-samples)
- [Anthropic Cookbook](https://github.com/anthropics/anthropic-cookbook)
