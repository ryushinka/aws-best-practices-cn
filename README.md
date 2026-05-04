# AWS 最佳实践（中文）

> 面向中国开发者与企业团队的 AWS 落地实践、架构模式与工具指南合集。
> 内容来自真实客户场景与团队沉淀，持续更新。

## 📚 内容目录

### 🤖 Kiro（AI 驱动开发环境）

- [Kiro 使用指南](./kiro/Kiro_User_Guide_CN.md) — 面向研发团队的快速上手与最佳实践

### 🔐 IAM 与安全

- [IAM 分组访问 EC2 控制台操作手册](./iam-security/IAM_EC2_Access_Control_Guide.md) — 基于标签的 EC2 实例分组权限隔离（中国区）

### ⏰ 每日自动化

- [每日自动化任务平台搭建指南](./daily-automation/Daily_Automation_Setup_Guide.md) — Lambda + EventBridge + SES 构建定时任务（账单报告等）

### 👥 研发协作

- [AI 时代的研发协作指南](./collaboration/AI_Era_RnD_Collaboration_Guide.md) — AI 原生团队协作模式

## 🗂️ 目录结构

```
aws-best-practices-cn/
├── kiro/                    # Kiro IDE 相关
├── iam-security/            # 身份、权限、访问控制
├── daily-automation/        # 定时自动化任务
└── collaboration/           # 团队协作
```

## 🤝 贡献

欢迎提 Issue 和 PR：

- 新增最佳实践：请放入对应主题目录，并在本 README 的目录中补充链接
- 修订已有内容：请在文档尾部追加变更说明（日期 + 修改点）
- 新主题：如需新增目录，请先开 Issue 讨论

## 📄 License

本仓库内容采用 [CC BY 4.0](./LICENSE) 协议发布，允许自由使用与再创作，请注明出处。

代码示例（若有）采用 MIT 协议。
