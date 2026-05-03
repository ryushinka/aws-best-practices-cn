# Kiro 使用指南

> 面向研发团队的 Kiro 快速上手与最佳实践
> 版本: v1.0 | 2026-05
> 官方文档: https://kiro.dev/docs

---

## 一、Kiro 是什么

Kiro 是 AWS 推出的 AI 驱动开发环境（Agentic IDE），基于 VS Code 构建，所有 VS Code 扩展都可以直接使用。

与传统 AI 编码助手（如 Copilot、Cursor）的核心区别：

| 维度 | 传统 AI 助手 | Kiro |
|------|------------|------|
| 工作方式 | 代码补全 / Chat 问答 | Spec 驱动：需求 → 设计 → 任务 → 代码 |
| 输出物 | 代码片段 | 完整的需求文档 + 设计文档 + 代码 + 测试 |
| 团队一致性 | 每个人各写各的 | Steering 统一团队规范 |
| 自动化 | 手动触发 | Hooks 事件驱动自动执行 |
| 扩展能力 | 插件 | Powers 按需加载专业知识 + MCP 连接外部工具 |

### 版本与价格

| 版本 | 月费 | Credits | 适用场景 |
|------|------|---------|---------|
| Free | $0 | 50 | 个人试用 |
| Pro | $20 | 1,000 | 日常开发 |
| Pro+ | $40 | 2,000 | 重度使用 |
| Power | $200 | 10,000 | 团队核心开发者 |
| Enterprise | 按需 | 按需 | 团队订阅，SSO，集中管理 |

超出 credits 后按 $0.04/credit 计费。底层模型为 Claude（Anthropic），包含在订阅中，无需额外付费。

### 下载安装

1. 访问 https://kiro.dev/downloads 下载对应平台安装包
2. 安装后使用 AWS Builder ID 或社交账号登录
3. 首次注册赠送 500 bonus credits（30 天内有效）

---

## 二、核心功能一：Agentic Chat（智能对话）

这是最基础的使用方式，打开 Chat 面板直接和 Kiro 对话。

### 打开方式

- 快捷键：`Cmd+L`（Mac）/ `Ctrl+L`（Windows/Linux）
- 命令面板：`Cmd+Shift+P` → 搜索 "Kiro: Open Chat"

### 两种模式

**Autopilot 模式**：Kiro 自主执行代码修改，适合信任度高的场景
**Supervised 模式**：每次修改后可以 review 和回退，适合谨慎操作

### 上下文引用

在聊天输入框中用 `#` 引用项目上下文，让 Kiro 更精准地理解你的意图：

| 引用方式 | 作用 | 示例 |
|---------|------|------|
| `#codebase` | 让 Kiro 自动查找相关文件 | `#codebase 解释认证流程` |
| `#file` | 引用特定文件 | `#auth.ts 解释这个实现` |
| `#folder` | 引用整个文件夹 | `#components/ 有哪些组件？` |
| `#git diff` | 引用当前 Git 变更 | `#git diff 解释这次改了什么` |
| `#terminal` | 引用终端输出 | `#terminal 帮我修复这个构建错误` |
| `#problems` | 引用当前文件的问题 | `#problems 帮我解决这些问题` |
| `#url` | 引用网页文档 | `#url:https://docs.example.com 解释这个 API` |
| `#steering` | 引用 steering 规范文件 | `#steering:coding-standards.md 审查我的代码` |
| `#spec` | 引用 spec 的所有文件 | `#spec:user-auth 更新设计文档` |

可以组合使用：`#codebase #auth.ts 解释认证如何与数据库交互`

### 常用场景

```
# 问代码逻辑
"解释这个项目的支付流程是怎么实现的"

# 生成新代码
"创建一个用户注册的 React 组件，包含表单验证"

# 修复问题
"这个函数报 TypeError，帮我修复"

# 重构代码
"把这个 class 组件重构成 hooks"

# 写测试
"给 utils/payment.ts 写单元测试"
```

### 多语言支持

Kiro 支持中文、英文、日文、韩文等多种语言对话，会自动检测并用相同语言回复。

---

## 三、核心功能二：Specs（规格驱动开发）

Specs 是 Kiro 最核心的差异化功能。它把"写代码"变成一个结构化的三阶段流程：

```
想法 → Requirements（需求） → Design（设计） → Tasks（任务） → 代码
```

### 为什么用 Spec

直接让 AI 写代码（Vibe Coding）的问题：
- 需求模糊时，AI 生成的代码"看起来对但方向错"
- 没有设计文档，后续维护困难
- 不同人写出来的代码风格不一致

Spec 驱动开发的好处：
- AI 先帮你把需求理清楚，再写代码
- 自动生成设计文档和架构图
- 任务拆解清晰，可以逐个执行和追踪

### 创建 Spec

1. 在 Kiro 面板的 Specs 区域点击 `+`
2. 选择类型：
   - **Feature Spec**：开发新功能
   - **Bugfix Spec**：修复 Bug
3. 用自然语言描述你的需求

### 三阶段流程

**阶段一：Requirements（需求定义）**

Kiro 会把你的描述转化为结构化的用户故事和验收标准，生成 `requirements.md`。

例如你说"做一个用户登录功能"，Kiro 会生成：
- 用户故事：作为用户，我希望能用邮箱和密码登录
- 验收标准：密码错误时显示错误提示、连续 5 次失败锁定账户、支持"记住我"...
- 你可以 review 并修改，确认后进入下一阶段

**阶段二：Design（技术设计）**

基于需求，Kiro 生成技术设计文档 `design.md`，包含：
- 系统架构和组件设计
- 时序图和数据流
- 错误处理策略
- 测试策略

**阶段三：Tasks（任务拆解与执行）**

Kiro 把设计拆解为具体的开发任务 `tasks.md`，每个任务：
- 有明确的完成标准
- 可以单独执行或批量执行
- 实时显示进度状态（待开始 / 进行中 / 已完成）

### Spec 文件结构

所有 spec 文件存储在项目的 `.kiro/specs/` 目录下：

```
.kiro/specs/
└── user-login/
    ├── requirements.md    # 需求文档
    ├── design.md          # 设计文档
    └── tasks.md           # 任务列表
```

### 什么时候用 Spec vs 直接 Chat

| 场景 | 推荐方式 |
|------|---------|
| 复杂功能开发，需要规划 | Spec |
| Bug 修复，担心引入回归 | Bugfix Spec |
| 需要团队协作的文档 | Spec |
| 快速原型、探索性编码 | 直接 Chat |
| 简单的代码修改 | 直接 Chat |

---

## 四、核心功能三：Steering（规范引导）

Steering 通过 Markdown 文件给 Kiro 提供持久化的项目知识，让它始终遵循你的团队规范。

### 解决什么问题

没有 Steering 时：
- 每次聊天都要重复说明"我们用 TypeScript"、"错误处理用这种格式"
- 不同人和 Kiro 对话，生成的代码风格不一致
- AI 不了解你的项目约定，经常用错库或模式

有了 Steering：
- 写一次规范，所有对话自动生效
- 团队所有人用 Kiro 生成的代码风格一致
- 新人加入团队，Kiro 自动按团队规范工作

### 文件位置

```
# 项目级（只对当前项目生效）
.kiro/steering/

# 全局级（对所有项目生效）
~/.kiro/steering/
```

项目级优先于全局级，有冲突时以项目级为准。

### 基础 Steering 文件

Kiro 可以自动生成三个基础文件：

1. 在 Kiro 面板的 Steering 区域点击 "Generate Steering Docs"
2. Kiro 会生成：
   - `product.md` — 产品概述：产品目标、用户群体、核心功能
   - `tech.md` — 技术栈：框架、库、开发工具、技术约束
   - `structure.md` — 项目结构：文件组织、命名约定、架构决策

### 自定义 Steering 文件

在 Kiro 面板 Steering 区域点击 `+`，创建自定义规范文件。

**示例：API 编码规范**

```markdown
# API 编码规范

## 错误处理
- 所有 API 必须返回统一的错误格式：{ code, message, details }
- 使用 HTTP 标准状态码，不要自定义状态码
- 500 错误不得暴露内部异常栈

## 命名约定
- REST 端点使用 kebab-case：/user-profiles
- 查询参数使用 camelCase：?pageSize=10
- 数据库字段使用 snake_case：created_at

## 安全
- 所有接口必须验证输入参数
- 敏感数据（密码、token）禁止出现在日志中
- 金额使用最小单位（分），类型为 integer
```

### 加载模式

通过文件顶部的 front matter 控制何时加载：

**始终加载（默认）** — 适合通用规范

```yaml
---
inclusion: always
---
```

**条件加载** — 只在编辑匹配文件时加载

```yaml
---
inclusion: fileMatch
fileMatchPattern: "**/*.tsx"
---
```

适合特定领域的规范，比如只在编辑 React 组件时加载组件规范。

支持多模式匹配：

```yaml
---
inclusion: fileMatch
fileMatchPattern: ["**/*.ts", "**/*.tsx", "**/tsconfig.*.json"]
---
```

**手动加载** — 在聊天中用 `#steering-file-name` 引用

```yaml
---
inclusion: manual
---
```

适合偶尔使用的指南，比如排障手册、迁移指南。

**自动加载** — Kiro 根据对话内容自动判断是否加载

```yaml
---
inclusion: auto
name: api-design
description: REST API 设计规范。在创建或修改 API 端点时使用。
---
```

### 引用项目文件

Steering 文件中可以引用项目中的其他文件，保持规范与代码同步：

```markdown
API 接口定义参考：#[[file:api/openapi.yaml]]
组件模板参考：#[[file:components/ui/button.tsx]]
环境变量说明：#[[file:.env.example]]
```

### 最佳实践

- **一个文件一个主题**：`api-standards.md`、`testing-patterns.md`、`security-policies.md`
- **解释"为什么"**：不只写规则，还要写原因，帮助 Kiro 理解意图
- **提供代码示例**：用 before/after 对比展示规范
- **不要放敏感信息**：Steering 文件是代码库的一部分，不要包含密钥、密码
- **定期维护**：架构变更时同步更新 Steering 文件

---

## 五、核心功能四：Hooks（自动化钩子）

Hooks 让 Kiro 在特定事件发生时自动执行预定义的动作，省去重复的手动操作。

### 典型场景

- 保存文件时自动跑 lint
- 提交代码前自动检查安全问题
- Spec 任务完成后自动跑测试
- 创建新文件时自动添加文件头注释

### 创建 Hook

1. 在 Kiro 面板的 Agent Hooks 区域点击 `+`
2. 选择创建方式：
   - **Ask Kiro to create a hook**：用自然语言描述，Kiro 自动生成配置
   - **Manually create a hook**：手动填写表单

也可以通过命令面板 `Cmd+Shift+P` → "Kiro: Open Kiro Hook UI" 打开。

### 触发事件类型

| 事件 | 触发时机 | 典型用途 |
|------|---------|---------|
| `fileEdited` | 用户保存文件 | 自动 lint、格式化 |
| `fileCreated` | 创建新文件 | 添加文件头、注册路由 |
| `fileDeleted` | 删除文件 | 清理引用 |
| `promptSubmit` | 发送消息给 Kiro | 预处理、添加上下文 |
| `agentStop` | Kiro 执行完成 | 后处理、通知 |
| `preToolUse` | 工具执行前 | 权限检查、参数验证 |
| `postToolUse` | 工具执行后 | 结果审查 |
| `preTaskExecution` | Spec 任务开始前 | 环境准备 |
| `postTaskExecution` | Spec 任务完成后 | 自动测试 |
| `userTriggered` | 手动触发 | 按需执行的工作流 |

### 动作类型

**askAgent**：让 Kiro 执行一个 prompt

```json
{
  "name": "Review Code Style",
  "version": "1.0.0",
  "when": {
    "type": "fileEdited",
    "patterns": ["*.ts", "*.tsx"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "检查刚保存的文件是否符合团队编码规范"
  }
}
```

**runCommand**：执行一个 shell 命令

```json
{
  "name": "Lint on Save",
  "version": "1.0.0",
  "when": {
    "type": "fileEdited",
    "patterns": ["*.ts", "*.tsx"]
  },
  "then": {
    "type": "runCommand",
    "command": "npm run lint"
  }
}
```

### 实用 Hook 示例

**保存时自动格式化**

```json
{
  "name": "Format on Save",
  "version": "1.0.0",
  "when": {
    "type": "fileEdited",
    "patterns": ["*.ts", "*.tsx", "*.js", "*.jsx"]
  },
  "then": {
    "type": "runCommand",
    "command": "npx prettier --write"
  }
}
```

**Spec 任务完成后跑测试**

```json
{
  "name": "Test After Task",
  "version": "1.0.0",
  "when": {
    "type": "postTaskExecution"
  },
  "then": {
    "type": "runCommand",
    "command": "npm run test"
  }
}
```

**写操作前安全审查**

```json
{
  "name": "Security Review",
  "version": "1.0.0",
  "when": {
    "type": "preToolUse",
    "toolTypes": ["write"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "检查这次写操作是否包含硬编码的密钥、密码或敏感信息"
  }
}
```

---

## 六、核心功能五：Powers（能力扩展包）

Powers 是 Kiro 的"专业知识包"，让 AI 在特定技术领域获得深度能力。

### 解决什么问题

连接多个 MCP 服务器时，所有工具定义会同时加载到上下文中，消耗大量 token，导致响应变慢。Powers 解决了这个问题：只在需要时加载相关的工具和知识。

### 工作原理

1. 你安装了 Stripe、Supabase、Datadog 等多个 Power
2. 当你说"添加支付功能"，Kiro 自动激活 Stripe Power
3. 当你转到"查询数据库"，Supabase Power 激活，Stripe 退出
4. 始终只加载相关的工具，保持响应速度

### 安装 Power

1. 访问 https://kiro.dev/powers 浏览可用的 Powers
2. 点击 "Install" 一键安装
3. 也可以在 Kiro 面板的 Powers 区域浏览和安装

### Power 包含什么

每个 Power 是一个完整的知识包：
- **POWER.md**：告诉 Kiro 有哪些工具可用、什么时候用
- **MCP 服务器配置**：工具和连接信息
- **Steering/Hooks**（可选）：自动化任务

### 推荐 Powers

以下是最实用的 Powers 精选，按场景分类：

#### AWS 云开发（强烈推荐）

| Power | 功能 | 推荐场景 |
|-------|------|---------|
| **AWS Infrastructure as Code** | CDK/CloudFormation 最佳实践、模板验证、安全合规检查 | IaC 开发必装 |
| **AWS SAM** | Serverless 应用开发、部署、管理 | Lambda/API Gateway 开发 |
| **AWS Amplify** | 全栈应用开发，认证、数据模型、存储 | 全栈 Web/Mobile 应用 |
| **AWS Step Functions** | 工作流编排，状态机设计 | 复杂业务流程编排 |
| **AWS Lambda Durable Functions** | 长时间运行的多步骤应用和 AI 工作流 | 需要持久化状态的 Lambda |
| **AWS Observability** | CloudWatch 日志/指标/告警 + CloudTrail 审计 | 运维监控排障 |
| **AWS DevOps Agent** | 事件调查、成本优化、架构审查 | 运维和 DevOps |
| **IAM Policy Autopilot** | 分析代码自动生成 IAM 策略 | 安全权限管理 |
| **AWS Transform** | 基础设施和软件现代化 | 迁移和现代化项目 |

#### 数据库

| Power | 功能 | 推荐场景 |
|-------|------|---------|
| **Aurora PostgreSQL** | Aurora PostgreSQL 最佳实践 | PostgreSQL 应用开发 |
| **Aurora DSQL** | Serverless PostgreSQL 兼容数据库，按需伸缩 | 需要弹性伸缩的数据库 |

#### AI / 智能应用

| Power | 功能 | 推荐场景 |
|-------|------|---------|
| **Strands Agent SDK** | 用 Bedrock/Anthropic/OpenAI 构建 AI Agent | AI Agent 开发 |
| **Amazon Bedrock AgentCore** | Agent 构建、部署、运营一体化平台 | 企业级 AI Agent |

#### 设计与前端

| Power | 功能 | 推荐场景 |
|-------|------|---------|
| **Figma** | 设计稿转代码、Code Connect、设计系统规则生成 | UI 开发，设计还原 |

#### 支付与 SaaS

| Power | 功能 | 推荐场景 |
|-------|------|---------|
| **Stripe** | 支付集成、订阅管理、退款处理 | 支付功能开发 |
| **Checkout.com** | 全球支付 API 文档和集成 | 跨境支付 |

#### 基础设施与部署

| Power | 功能 | 推荐场景 |
|-------|------|---------|
| **Terraform** | IaC 开发、Registry 查询、HCP 管理 | Terraform 用户 |
| **Netlify** | 前端应用部署到全球 CDN | 前端部署 |

#### 测试与 API

| Power | 功能 | 推荐场景 |
|-------|------|---------|
| **Postman** | API 测试自动化、Collection 管理、环境配置 | API 开发测试 |

> 完整列表和一键安装：https://kiro.dev/powers

---

## 七、核心功能六：MCP 服务器（外部工具连接）

MCP（Model Context Protocol）让 Kiro 连接外部工具和数据源。Powers 内置了 MCP 配置，但你也可以手动配置独立的 MCP 服务器。

### 配置方式

在项目根目录创建 `.kiro/settings/mcp.json`：

```json
{
  "mcpServers": {
    "aws-docs": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

全局配置（所有项目生效）放在 `~/.kiro/settings/mcp.json`。

> 注意：MCP 服务器通常使用 `uvx` 命令运行，需要先安装 `uv`（Python 包管理器）。安装方式参考：https://docs.astral.sh/uv/getting-started/installation/

### 推荐 MCP 服务器

#### AWS 官方 MCP 服务器

| MCP 服务器 | 用途 | 安装命令 |
|-----------|------|---------|
| **AWS Documentation** | 搜索和阅读 AWS 官方文档 | `uvx awslabs.aws-documentation-mcp-server@latest` |
| **AWS CDK** | CDK 项目开发辅助 | `uvx awslabs.cdk-mcp-server@latest` |
| **AWS CloudFormation** | CFN 模板验证和安全检查 | `uvx awslabs.cfn-mcp-server@latest` |
| **AWS Cost Analysis** | AWS 成本分析 | `uvx awslabs.cost-analysis-mcp-server@latest` |
| **AWS Diagram** | 生成 AWS 架构图 | `uvx awslabs.aws-diagram-mcp-server@latest` |
| **Amazon Nova Canvas** | AI 图片生成 | `uvx awslabs.nova-canvas-mcp-server@latest` |
| **Amazon Bedrock KB** | Bedrock 知识库检索 | `uvx awslabs.bedrock-kb-retrieval-mcp-server@latest` |
| **AWS Lambda** | Lambda 函数管理 | `uvx awslabs.lambda-mcp-server@latest` |
| **Amazon S3** | S3 存储桶操作 | `uvx awslabs.s3-mcp-server@latest` |
| **Amazon DynamoDB** | DynamoDB 表操作 | `uvx awslabs.dynamodb-mcp-server@latest` |
| **Amazon ECS** | ECS 容器服务管理 | `uvx awslabs.ecs-mcp-server@latest` |
| **Amazon Aurora PostgreSQL** | Aurora PostgreSQL 操作 | `uvx awslabs.postgres-mcp-server@latest` |

> 完整 AWS MCP 列表：https://github.com/awslabs/mcp

#### 通用开发 MCP 服务器

| MCP 服务器 | 用途 | 说明 |
|-----------|------|------|
| **Filesystem** | 文件系统读写操作 | Kiro 内置 |
| **GitHub** | GitHub 仓库、PR、Issues 操作 | 需要 GitHub Token |
| **GitLab** | GitLab 项目管理 | 需要 GitLab Token |
| **PostgreSQL** | 通用 PostgreSQL 数据库操作 | 需要数据库连接信息 |
| **MySQL** | MySQL 数据库操作 | 需要数据库连接信息 |
| **SQLite** | 轻量级数据库操作 | 本地文件即可 |
| **Redis** | Redis 缓存操作 | 需要 Redis 连接信息 |
| **Docker** | Docker 容器管理 | 需要 Docker 运行环境 |
| **Kubernetes** | K8s 集群管理 | 需要 kubeconfig |
| **Brave Search** | 网络搜索 | 需要 Brave API Key |
| **Puppeteer** | 浏览器自动化 | 需要 Chrome/Chromium |
| **Slack** | Slack 消息和频道管理 | 需要 Slack Token |

### MCP 配置示例

**多个 MCP 服务器组合配置**：

```json
{
  "mcpServers": {
    "aws-docs": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"],
      "env": { "FASTMCP_LOG_LEVEL": "ERROR" },
      "autoApprove": ["search_documentation", "read_documentation"]
    },
    "aws-cfn": {
      "command": "uvx",
      "args": ["awslabs.cfn-mcp-server@latest"],
      "env": { "FASTMCP_LOG_LEVEL": "ERROR" },
      "autoApprove": []
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "<your-token>" },
      "autoApprove": []
    }
  }
}
```

### Powers vs MCP：怎么选

| 维度 | Powers | 独立 MCP |
|------|--------|---------|
| 安装方式 | 一键安装，零配置 | 手动编辑 JSON 配置 |
| 上下文管理 | 按需加载，不浪费 token | 全部加载，可能过载 |
| 包含内容 | MCP + Steering + Hooks 完整包 | 只有工具 |
| 适用场景 | 有对应 Power 时优先用 | Power 不覆盖的工具 |

**建议**：有 Power 的优先装 Power，没有 Power 的再手动配 MCP

#### 社区精选开源 MCP 服务器

以下是社区高星开源 MCP，可以直接在 Kiro 中配置使用：

| MCP 服务器 | GitHub | 功能 | 推荐理由 |
|-----------|--------|------|---------|
| **Context7** | `upstash/context7` | 实时查询任意库/框架的最新文档和代码示例 | 解决 AI 用过时 API 的问题，查文档神器 |
| **Sequential Thinking** | `modelcontextprotocol/servers` | 动态思维链推理，支持修正和分支 | 复杂问题拆解，比普通 prompt 更深入 |
| **Memory** | `modelcontextprotocol/servers` | 基于知识图谱的持久化记忆 | 跨会话记住项目上下文和决策 |
| **Playwright** | `microsoft/playwright-mcp` | 浏览器自动化，支持截图和交互 | 端到端测试、网页数据抓取 |
| **Puppeteer** | `modelcontextprotocol/servers` | Chrome 浏览器控制和自动化 | 轻量级浏览器自动化 |
| **Git** | `modelcontextprotocol/servers` | Git 仓库操作（log、diff、branch） | 代码版本管理 |
| **GitHub** | `modelcontextprotocol/servers` | GitHub API 全功能（PR、Issues、Actions） | GitHub 工作流自动化 |
| **Fetch** | `modelcontextprotocol/servers` | 网页内容抓取，自动转 Markdown | 读文档、抓参考资料 |
| **Filesystem** | `modelcontextprotocol/servers` | 安全的文件系统读写 | 基础文件操作 |
| **Docker** | `docker/docker-mcp` | Docker 容器和镜像管理 | 容器化开发 |
| **Kubernetes** | `strowk/mcp-k8s-go` | K8s 集群资源查询和管理 | K8s 运维 |
| **Sentry** | `getsentry/sentry-mcp` | 查询 Sentry 错误和性能数据 | 生产环境排障 |
| **Linear** | `linear/linear-mcp-server` | Linear 项目管理（Issues、Projects） | 项目管理集成 |
| **Notion** | `makenotion/notion-mcp-server` | Notion 页面和数据库操作 | 文档和知识库管理 |
| **Slack** | `modelcontextprotocol/servers` | Slack 消息和频道管理 | 团队沟通集成 |

> 更多开源 MCP：https://github.com/punkpeye/awesome-mcp-servers（85K+ Stars）

**配置示例 — Context7（查文档神器）**：

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"],
      "autoApprove": []
    }
  }
}
```

使用时在 Chat 中说"用 context7 查一下 Next.js 15 的 Server Actions 用法"，Kiro 会实时拉取最新文档。

---

## 八、高级使用技巧

掌握基础功能后，以下技巧可以进一步提升效率。

### 1. Design-First Spec：从架构开始

除了默认的 Requirements-First 流程，Kiro 还支持 **Design-First** 工作流：先定义技术架构，再反推需求。

**适用场景**：
- 技术驱动的项目（如基础设施重构、性能优化）
- 已有明确技术方案，需要补充需求文档
- 架构师主导的设计评审

**使用方式**：创建 Feature Spec 时选择 "Design-First"，先写 `design.md`，Kiro 会从设计反推出 `requirements.md`。

> 参考：[Design-First Workflow](https://kiro.dev/docs/specs/feature-specs/tech-design-first/)

### 2. Bugfix Spec：结构化修 Bug

不要直接让 Kiro "修这个 bug"，用 Bugfix Spec 可以避免引入回归：

1. 创建 Spec 时选择 "Bug"
2. Kiro 会生成 `bugfix.md`，包含：
   - **当前行为**：Bug 的具体表现
   - **期望行为**：正确的行为应该是什么
   - **不变行为**：修复后不应该改变的行为（防回归）
3. 基于分析生成设计和任务

这比直接 Chat 修 Bug 更安全，特别是在复杂系统中。

> 参考：[Bugfix Specs](https://kiro.dev/docs/specs/bugfix-specs/)

### 3. Steering 的 Auto 模式：智能按需加载

当 Steering 文件越来越多时，用 `auto` 模式让 Kiro 自动判断何时加载：

```yaml
---
inclusion: auto
name: database-patterns
description: 数据库设计模式和查询优化指南。在创建或修改数据库相关代码时使用。
---

# 数据库设计模式
...
```

当你和 Kiro 讨论数据库相关话题时，这个文件会自动加载；讨论前端时则不会。比 `always` 省 token，比 `manual` 省操作。

### 4. 全局 Steering：个人偏好跨项目生效

把个人编码偏好放在全局 Steering 中（`~/.kiro/steering/`），所有项目自动生效：

```markdown
# 我的编码偏好

## 通用
- 优先使用 TypeScript，避免 any 类型
- 错误处理使用 Result 模式而非 try-catch
- 注释用中文

## Git
- commit message 用英文，格式：type(scope): description
- 每个 commit 只做一件事
```

这相当于你的"AI 编码助手个性化配置"，换项目也不用重新说明。

> 参考：[Global Steering](https://kiro.dev/blog/stop-repeating-yourself/)

### 5. Steering 引用外部文件：让规范和代码同步

在 Steering 中引用项目文件，Kiro 会读取最新内容：

```markdown
# API 开发规范

接口定义以 OpenAPI spec 为准：
#[[file:api/openapi.yaml]]

数据模型参考 Prisma schema：
#[[file:prisma/schema.prisma]]

环境变量说明：
#[[file:.env.example]]
```

这样 API spec 更新后，Kiro 自动按最新定义生成代码，不需要手动同步。

### 6. Hook 链式自动化：文件保存触发完整流水线

组合多个 Hook 实现保存即验证的完整流水线：

```
保存 .ts 文件
  ├─ Hook 1: 自动格式化（runCommand: prettier）
  ├─ Hook 2: 类型检查（runCommand: tsc --noEmit）
  └─ Hook 3: 安全审查（askAgent: 检查敏感信息）
```

每个 Hook 独立配置，按事件并行触发。

### 7. preToolUse Hook：写操作前的安全门禁

在 Kiro 执行写操作前自动检查，防止 AI 写入不安全的代码：

```json
{
  "name": "Write Guard",
  "version": "1.0.0",
  "when": {
    "type": "preToolUse",
    "toolTypes": ["write"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "在写入前检查：1) 是否有硬编码的密钥或密码 2) 是否有未经验证的用户输入 3) SQL 是否使用参数化查询 4) 是否符合团队 Steering 规范。如果发现问题，修正后再写入。"
  }
}
```

### 8. Spec 中引用外部文档

Spec 文件支持 `#[[file:...]]` 引用，可以把 OpenAPI spec、GraphQL schema 等作为输入：

在 `requirements.md` 中：
```markdown
## 参考文档
API 接口定义：#[[file:api/openapi.yaml]]
数据库 Schema：#[[file:prisma/schema.prisma]]
```

Kiro 会读取这些文件的内容，生成的设计和代码会严格遵循已有的接口定义。

### 9. Kiro CLI：终端中使用 Kiro

Kiro 不只是 IDE，还有命令行版本，适合 CI/CD 集成和终端重度用户：

- 支持 Spec、Steering、MCP、Sub-agent 等核心功能
- 可以在 CI/CD 流水线中自动执行 Spec 任务
- 支持自定义 Agent 和并行子任务

> 参考：[Kiro CLI](https://kiro.dev/cli/)

### 10. Autonomous Agent：让 Kiro 独立完成任务

Kiro 的 Autonomous Agent（预览中）可以独立执行开发任务，无需持续交互：

- 维持上下文，从每次交互中学习
- 适合耗时较长的任务（大规模重构、批量迁移）
- Pro、Pro+、Power 订阅用户可用

> 参考：[Autonomous Agent](https://kiro.dev/autonomous-agent/)

---

## 九、团队协作最佳实践

### 1. 建立团队 Steering 文件库

把团队的编码规范、架构约定、安全策略写成 Steering 文件，提交到代码仓库：

```
.kiro/steering/
├── product.md              # 产品概述（自动生成）
├── tech.md                 # 技术栈（自动生成）
├── structure.md            # 项目结构（自动生成）
├── api-standards.md        # API 规范
├── testing-patterns.md     # 测试规范
├── security-policies.md    # 安全策略
└── deployment-workflow.md  # 部署流程
```

新人加入团队，clone 代码后 Kiro 自动加载所有规范，立即按团队标准工作。

### 2. 用 Spec 管理功能开发

- 每个功能用一个 Spec，需求、设计、任务都有文档
- Spec 文件提交到代码仓库，可以 code review
- 产品和研发一起 review requirements.md，确保对齐

### 3. 用 Hooks 统一质量门禁

- 保存时自动 lint + format
- Spec 任务完成后自动跑测试
- 写操作前检查安全规范

### 4. 渐进式采纳

不需要一步到位，建议的采纳路径：

```
第 1 周：Chat 基础使用
  └─ 熟悉对话、上下文引用、代码生成

第 2 周：Steering 规范建立
  └─ 生成基础文件 + 添加团队自定义规范

第 3 周：Spec 驱动开发
  └─ 选一个中等复杂度的功能，完整走一遍 Spec 流程

第 4 周：Hooks 自动化
  └─ 配置 lint、测试、安全检查等自动化钩子

持续：Powers + MCP 扩展
  └─ 根据项目需要安装 Powers 和配置 MCP 服务器
```

---

## 十、常用快捷键

| 操作 | Mac | Windows/Linux |
|------|-----|---------------|
| 打开 Chat | `Cmd+L` | `Ctrl+L` |
| 打开命令面板 | `Cmd+Shift+P` | `Ctrl+Shift+P` |
| 打开 Chat 侧边栏 | `Cmd+Opt+B` | `Ctrl+Alt+B` |

---

## 十一、常见问题

**Q: Kiro 和 Cursor / Copilot 有什么区别？**
A: Kiro 的核心差异是 Spec 驱动开发（从需求到代码的完整流程）和 Steering（团队规范持久化）。Cursor/Copilot 侧重代码补全和 Chat，Kiro 侧重把整个开发流程结构化。

**Q: Kiro 用的是什么 AI 模型？**
A: 底层使用 Anthropic 的 Claude 模型（包括 Claude Opus 和 Sonnet），包含在订阅费用中，不需要额外付 API 费用。

**Q: Steering 文件会被发送到云端吗？**
A: Steering 文件的内容会作为上下文发送给 AI 模型，用于生成更准确的代码。不要在 Steering 文件中放置密钥、密码等敏感信息。

**Q: 可以离线使用吗？**
A: Kiro 需要网络连接来调用 AI 模型。编辑器本身的基础功能（代码编辑、文件管理）可以离线使用。

**Q: 支持哪些编程语言？**
A: Kiro 支持所有主流编程语言，包括但不限于 TypeScript/JavaScript、Python、Java、Go、Rust、C/C++、Ruby、PHP 等。

**Q: 团队如何统一管理订阅？**
A: 使用 Kiro Enterprise 版本，支持集中计费、SSO（通过 AWS IAM Identity Center）、使用量分析和组织管理。

---

## 附录：参考资源

| 资源 | 链接 |
|------|------|
| 官方文档 | https://kiro.dev/docs |
| 下载安装 | https://kiro.dev/downloads |
| Powers 市场 | https://kiro.dev/powers |
| 价格方案 | https://kiro.dev/pricing |
| 企业版 | https://kiro.dev/enterprise |
| Kiro CLI | https://kiro.dev/cli |
| Autonomous Agent | https://kiro.dev/autonomous-agent |
| Discord 社区 | https://kiro.dev/discord |
| 更新日志 | https://kiro.dev/changelog |
| 报告 Bug | https://github.com/kirodotdev/Kiro/issues |
| AWS MCP 服务器合集 | https://github.com/awslabs/mcp |
| 社区 MCP 合集 (85K+ Stars) | https://github.com/punkpeye/awesome-mcp-servers |
| Book of Kiro（社区指南） | https://kiro-community.github.io/book-of-kiro |
| Kiro 最佳实践模板 | https://repost.aws/articles/ARXfJeAJ14Sh65Odc0rw6wOg |

### 推荐阅读

| 文章 | 来源 | 内容 |
|------|------|------|
| [From Chat to Specs: Deep Dive](https://kiro.dev/blog/from-chat-to-specs-deep-dive/) | Kiro 官方 | Spec 驱动开发的深度解析 |
| [Stop Repeating Yourself](https://kiro.dev/blog/stop-repeating-yourself/) | Kiro 官方 | 全局 Steering 的最佳实践 |
| [Automate with Agent Hooks](https://kiro.dev/blog/automate-your-development-workflow-with-agent-hooks/) | Kiro 官方 | Hooks 自动化工作流详解 |
| [Specs: Bugfix and Design-First](https://kiro.dev/blog/specs-bugfix-and-design-first/) | Kiro 官方 | Bugfix Spec 和 Design-First 工作流 |
| [Introducing Kiro CLI](https://kiro.dev/blog/introducing-kiro-cli/) | Kiro 官方 | CLI 版本介绍和使用 |
| [Introducing Powers](https://kiro.dev/blog/introducing-powers/) | Kiro 官方 | Powers 机制详解 |
| [Drug Discovery Agent with Kiro](https://aws.amazon.com/blogs/industries/from-spec-to-production-a-three-week-drug-discovery-agent-using-kiro/) | AWS Blog | 用 Kiro 三周构建药物发现 Agent（LSHC 案例） |
| [Agentic Cloud Modernization](https://aws.amazon.com/blogs/migration-and-modernization/agentic-cloud-modernization-accelerating-modernization-with-aws-mcps-and-kiro/) | AWS Blog | 用 Kiro + MCP 加速云迁移现代化 |

---

*基于 Kiro 官方文档 (kiro.dev/docs) 整理 | 2026-05*
