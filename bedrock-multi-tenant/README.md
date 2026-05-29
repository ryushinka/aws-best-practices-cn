# Bedrock Inference Profile 多子公司分账方案

## 场景

- 一个母公司 AWS 账号
- 两个（或多个）子公司共用该账号通过 Amazon Bedrock 调用 Claude 模型
- 通过 Application Inference Profile + Cost Allocation Tag 实现精确分账
- 无需额外服务（Lambda、API Gateway 等），无额外费用

## 方案核心

为每个子公司创建独立的 Application Inference Profile，打上不同的 `company` Tag。调用时使用各自的 Profile ARN，Cost Explorer 自动按 Tag 分账。

## 文档

- [完整控制台操作指南](./Bedrock_Multi_Tenant_Console_Guide.md) — 包含从创建 Profile 到查看分账的全部步骤和代码示例

## 快速开始

1. 在 Bedrock 控制台创建 Application Inference Profile（每个子公司一个，打上 Tag）
2. 在 Billing 控制台激活 Cost Allocation Tag
3. 调用时 `modelId` 填对应子公司的 Profile ARN
4. 24 小时后在 Cost Explorer 按 Tag 查看分账
