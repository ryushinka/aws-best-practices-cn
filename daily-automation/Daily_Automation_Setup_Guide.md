# AWS 每日自动化任务平台 — 搭建指南

> **Project Tag**: `daily-automation`
> **Region**: us-west-2 (Oregon)
> **Account**: 570326752681

---

## 架构总览

```
EventBridge Scheduler (cron)
  ├── 07:00 北京 → Lambda: daily-bill-report    → Cost Explorer → SES 邮件
  ├── 08:00 北京 → Lambda: daily-news           → RSS/API + Bedrock 摘要 → SES（待建）
  ├── 08:30 北京 → Lambda: daily-planner        → Graph API (邮件+日历) → Bedrock → SES（待建）
  └── 周一 09:00 → Lambda: resource-check       → AWS APIs → SES（待建）
```

---

## 已完成：每日账单报告

### 资源清单

| 资源 | 名称/ARN | 标签 |
|---|---|---|
| Lambda | `daily-bill-report` | Project=daily-automation, Component=bill-report |
| EventBridge Rule | `daily-bill-report-schedule` | 同上 |
| IAM Role | `daily-bill-report-lambda-role` | 同上 |
| CloudWatch Logs | `/aws/lambda/daily-bill-report` | 同上 |
| SES Identity | `zhhliu@amazon.com`（已验证） | 不支持标签 |

### 触发时间

- **cron 表达式**: `cron(0 23 * * ? *)` (UTC 23:00 = 北京时间 07:00)

### Lambda 代码逻辑

1. 调用 Cost Explorer API 查询前一天按服务分类的费用
2. 查询本月累计费用
3. 生成 HTML 邮件（服务明细表格 + 昨日合计 + 本月累计）
4. 通过 SES 发送到 `zhhliu@amazon.com`

### 邮件效果

```
主题：AWS 每日账单 — 2026-05-03 | 合计 $32.15

服务                        费用 (USD)
─────────────────────────────────────
Amazon EC2 - Compute       $8.52
Amazon VPC                 $7.98
Kiro                       $6.67
...
─────────────────────────────────────
昨日合计                    $32.15
本月累计                    $128.60
```

### 月费

| 项目 | 费用 |
|---|---|
| Cost Explorer API（30 次/月） | $0.30 |
| Lambda + SES | 免费额度内 |
| **合计** | **~$0.30/月** |

---

## 搭建步骤（可复制给他人）

### 前提条件

- AWS CLI 已配置
- 有 IAM、Lambda、EventBridge、SES、Cost Explorer 权限

### Step 1：验证 SES 邮箱

```bash
aws ses verify-email-identity \
  --email-address <你的邮箱> \
  --region us-west-2
```

去邮箱点击验证链接。

### Step 2：创建 IAM Role

```bash
# 创建角色
aws iam create-role \
  --role-name daily-bill-report-lambda-role \
  --assume-role-policy-document '{
    "Version":"2012-10-17",
    "Statement":[{
      "Effect":"Allow",
      "Principal":{"Service":"lambda.amazonaws.com"},
      "Action":"sts:AssumeRole"
    }]
  }'

# 附加权限策略
aws iam put-role-policy \
  --role-name daily-bill-report-lambda-role \
  --policy-name daily-bill-report-policy \
  --policy-document '{
    "Version":"2012-10-17",
    "Statement":[
      {"Effect":"Allow","Action":["ce:GetCostAndUsage"],"Resource":"*"},
      {"Effect":"Allow","Action":["ses:SendEmail"],"Resource":"*"},
      {"Effect":"Allow","Action":["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],"Resource":"arn:aws:logs:*:*:*"}
    ]
  }'
```

### Step 3：创建 Lambda 函数

将以下代码保存为 `lambda_function.py` 并打包为 zip：

```python
import boto3
from datetime import datetime, timedelta

RECIPIENT = "<你的邮箱>"
SENDER = "<你的邮箱>"
SES_REGION = "us-west-2"

def lambda_handler(event, context):
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
    today = datetime.utcnow().strftime('%Y-%m-%d')
    first_of_month = datetime.utcnow().replace(day=1).strftime('%Y-%m-%d')

    ce = boto3.client('ce', region_name='us-east-1')

    daily = ce.get_cost_and_usage(
        TimePeriod={'Start': yesterday, 'End': today},
        Granularity='DAILY',
        Metrics=['UnblendedCost'],
        GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
    )

    mtd = ce.get_cost_and_usage(
        TimePeriod={'Start': first_of_month, 'End': today},
        Granularity='MONTHLY',
        Metrics=['UnblendedCost']
    )

    mtd_total = float(mtd['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])

    services = []
    total = 0
    for g in daily['ResultsByTime'][0].get('Groups', []):
        cost = float(g['Metrics']['UnblendedCost']['Amount'])
        if cost > 0.005:
            services.append((g['Keys'][0], cost))
            total += cost
    services.sort(key=lambda x: -x[1])

    rows = ""
    for svc, cost in services:
        rows += f"<tr><td style='padding:6px 12px;border-bottom:1px solid #eee'>{svc}</td>"
        rows += f"<td style='padding:6px 12px;border-bottom:1px solid #eee;text-align:right'>${cost:.2f}</td></tr>"

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
      <h2 style="color:#232f3e">☁️ AWS 每日账单 — {yesterday}</h2>
      <table style="width:100%;border-collapse:collapse;margin:16px 0">
        <tr style="background:#232f3e;color:white">
          <th style="padding:8px 12px;text-align:left">服务</th>
          <th style="padding:8px 12px;text-align:right">费用 (USD)</th>
        </tr>
        {rows}
        <tr style="background:#f5f5f5;font-weight:bold">
          <td style="padding:8px 12px">昨日合计</td>
          <td style="padding:8px 12px;text-align:right">${total:.2f}</td>
        </tr>
        <tr style="background:#fff3cd;font-weight:bold">
          <td style="padding:8px 12px">📊 本月累计</td>
          <td style="padding:8px 12px;text-align:right">${mtd_total:.2f}</td>
        </tr>
      </table>
      <p style="color:#666;font-size:12px">数据来源: AWS Cost Explorer (有 ~12h 延迟)</p>
    </div>
    """

    ses = boto3.client('ses', region_name=SES_REGION)
    ses.send_email(
        Source=SENDER,
        Destination={'ToAddresses': [RECIPIENT]},
        Message={
            'Subject': {'Data': f'AWS 每日账单 — {yesterday} | 合计 ${total:.2f}', 'Charset': 'UTF-8'},
            'Body': {'Html': {'Data': html, 'Charset': 'UTF-8'}}
        }
    )
    return {'statusCode': 200, 'body': f'Sent bill report for {yesterday}'}
```

```bash
# 打包并创建 Lambda
zip -j daily-bill.zip lambda_function.py

aws lambda create-function \
  --function-name daily-bill-report \
  --runtime python3.12 \
  --handler lambda_function.lambda_handler \
  --role arn:aws:iam::<ACCOUNT_ID>:role/daily-bill-report-lambda-role \
  --zip-file fileb://daily-bill.zip \
  --timeout 30 \
  --memory-size 128 \
  --region us-west-2
```

### Step 4：创建 EventBridge 定时触发

```bash
# 创建规则（UTC 23:00 = 北京 07:00）
aws events put-rule \
  --name daily-bill-report-schedule \
  --schedule-expression "cron(0 23 * * ? *)" \
  --state ENABLED \
  --region us-west-2

# 授权 EventBridge 调用 Lambda
aws lambda add-permission \
  --function-name daily-bill-report \
  --statement-id eventbridge-daily-bill \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-west-2:<ACCOUNT_ID>:rule/daily-bill-report-schedule \
  --region us-west-2

# 绑定目标
aws events put-targets \
  --rule daily-bill-report-schedule \
  --targets '[{"Id":"daily-bill-lambda","Arn":"arn:aws:lambda:us-west-2:<ACCOUNT_ID>:function:daily-bill-report"}]' \
  --region us-west-2
```

### Step 5：打标签

```bash
aws lambda tag-resource \
  --resource arn:aws:lambda:us-west-2:<ACCOUNT_ID>:function:daily-bill-report \
  --tags Project=daily-automation,Owner=<你的alias>,Component=bill-report \
  --region us-west-2

aws events tag-resource \
  --resource-arn arn:aws:events:us-west-2:<ACCOUNT_ID>:rule/daily-bill-report-schedule \
  --tags '[{"Key":"Project","Value":"daily-automation"},{"Key":"Owner","Value":"<你的alias>"},{"Key":"Component","Value":"bill-report"}]' \
  --region us-west-2

aws iam tag-role \
  --role-name daily-bill-report-lambda-role \
  --tags '[{"Key":"Project","Value":"daily-automation"},{"Key":"Owner","Value":"<你的alias>"},{"Key":"Component","Value":"bill-report"}]'

aws logs tag-log-group \
  --log-group-name /aws/lambda/daily-bill-report \
  --tags Project=daily-automation,Owner=<你的alias>,Component=bill-report \
  --region us-west-2
```

### Step 6：测试

```bash
aws lambda invoke \
  --function-name daily-bill-report \
  --payload '{}' \
  --region us-west-2 \
  /tmp/output.json && cat /tmp/output.json
```

---

## 待建任务

| 任务 | 触发时间 | Component 标签 | 状态 |
|---|---|---|---|
| 每日账单报告 | 07:00 | `bill-report` | ✅ 已完成 |
| 每日新闻摘要 | 08:00 | `daily-news` | 🔲 待建 |
| 昨日邮件汇总 + 今日规划 | 08:30 | `daily-planner` | 🔲 待建 |
| 每周闲置资源检查 | 周一 09:00 | `resource-check` | 🔲 待建 |

### 新增任务模式

每个新任务复用同样的模式：
1. 创建 Lambda 函数（新代码）
2. 创建 EventBridge Rule（新 cron）
3. IAM Role 可复用或新建
4. 统一打标签 `Project=daily-automation`

---

## 标签规范

| 标签 | 值 | 说明 |
|---|---|---|
| `Project` | `daily-automation` | 所有任务统一项目标识 |
| `Owner` | 你的 alias | 资源归属 |
| `Component` | 任务名称 | 区分不同任务 |

## 控制台入口

| 资源 | URL |
|---|---|
| Lambda | https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions |
| EventBridge Rules | https://us-west-2.console.aws.amazon.com/events/home?region=us-west-2#/rules |
| SES Identities | https://us-west-2.console.aws.amazon.com/ses/home?region=us-west-2#/identities |
| CloudWatch Logs | https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#logsV2:log-groups |
| Tag Editor | https://us-west-2.console.aws.amazon.com/resource-groups/tag-editor/find-resources?region=us-west-2 |
