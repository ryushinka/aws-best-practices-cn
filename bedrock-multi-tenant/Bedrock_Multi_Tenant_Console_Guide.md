# Bedrock Inference Profile 多子公司分账 — 完整控制台操作指南

## 场景说明

- 母公司拥有一个 AWS 账号
- 两个子公司（A、B）共用该账号通过 Amazon Bedrock 调用 Claude 模型
- 通过 Inference Profile + Cost Allocation Tag 实现精确分账
- 无需额外服务，无额外费用

---

## 前置条件

- 拥有 AWS 账号的管理员权限（或至少有 Bedrock、Billing 权限）
- Anthropic Claude 模型首次使用可能需要提交用例说明（之后自动启用）
- 确认使用的 Claude 模型版本（如 Claude Sonnet 4、Claude Haiku 等）

---

## Step 1：创建 Inference Profile（为每个子公司各创建一个）

### 1.1 创建子公司 A 的 Profile

1. 进入 **Amazon Bedrock** 控制台
2. 左侧菜单选择 **Inference profiles**（推理配置文件）
3. 点击 **Create application inference profile**
4. 填写：
   - **Inference profile name**: `bedrock-subsidiary-a`
   - **Select model**: 选择一个系统定义的 Inference Profile 作为来源，如 `US Anthropic Claude Sonnet 4.6`
   - **Tags**:
     - Key: `company`
     - Value: `subsidiary-a`
5. 点击 **Create**
6. 记录生成的 **Application Inference Profile ARN**，格式类似：
   ```
   arn:aws:bedrock:us-east-1:123456789012:application-inference-profile/ys6bahmkdzrl
   ```

> ⚠️ **注意**：Claude 4.x 系列模型的推理类型为 `INFERENCE_PROFILE`（非 `ON_DEMAND`），创建自定义 Profile 时需要从系统定义的 Inference Profile 复制，而不是直接选择 Foundation Model。

### 1.2 创建子公司 B 的 Profile

重复上述步骤，但使用：
- **Name**: `bedrock-subsidiary-b`
- **Tag**: Key=`company`, Value=`subsidiary-b`

---

## Step 2：激活 Cost Allocation Tag

1. 进入 **Billing and Cost Management** 控制台
2. 左侧菜单选择 **Cost allocation tags**
3. 选择 **User-defined cost allocation tags** 标签页
4. 在搜索框中输入 `company`
5. 勾选 `company` 标签
6. 点击 **Activate**
7. ⏰ **等待 24 小时**，标签才会在 Cost Explorer 中生效

---

## Step 3：测试调用

使用现有的 AWS 凭证（IAM User 或 Role），调用时指定对应子公司的 Profile ARN 即可：

### 子公司 A 测试

```python
import boto3

client = boto3.client("bedrock-runtime", region_name="us-east-1")

response = client.converse(
    modelId="arn:aws:bedrock:us-east-1:你的AccountID:application-inference-profile/你的ProfileID-A",
    messages=[
        {"role": "user", "content": [{"text": "你好，请用中文介绍一下你自己"}]}
    ],
    inferenceConfig={"maxTokens": 512},
)

print(response["output"]["message"]["content"][0]["text"])
print(f"Token 用量: {response['usage']}")
```

### 子公司 B 测试

同上，将 Profile ARN 替换为子公司 B 的：

```python
response = client.converse(
    modelId="arn:aws:bedrock:us-east-1:你的AccountID:application-inference-profile/你的ProfileID-B",
    messages=[
        {"role": "user", "content": [{"text": "你好，请用中文介绍一下你自己"}]}
    ],
    inferenceConfig={"maxTokens": 512},
)
```

### 应用层按子公司路由的示例

```python
import boto3

# 各子公司的 Application Inference Profile ARN 映射（创建后从控制台获取）
PROFILES = {
    "subsidiary-a": "arn:aws:bedrock:us-east-1:你的AccountID:application-inference-profile/你的ProfileID-A",
    "subsidiary-b": "arn:aws:bedrock:us-east-1:你的AccountID:application-inference-profile/你的ProfileID-B",
}

client = boto3.client("bedrock-runtime", region_name="us-east-1")

def call_claude(company: str, message: str) -> str:
    """根据子公司名称路由到对应的 Inference Profile"""
    response = client.converse(
        modelId=PROFILES[company],
        messages=[{"role": "user", "content": [{"text": message}]}],
        inferenceConfig={"maxTokens": 1024, "temperature": 0.7},
    )
    result = response["output"]["message"]["content"][0]["text"]
    usage = response["usage"]
    print(f"[{company}] 输入: {usage['inputTokens']} tokens, 输出: {usage['outputTokens']} tokens")
    return result

# 子公司 A 的请求
call_claude("subsidiary-a", "帮我写一段产品介绍")

# 子公司 B 的请求
call_claude("subsidiary-b", "帮我翻译这段文字")
```

---

## Step 4：查看分账报告

> 首次激活 Tag 后需等待 24 小时，之后的费用才会按 Tag 分类。

1. 进入 **Billing and Cost Management** 控制台
2. 左侧选择 **Cost Explorer**
3. 点击 **Launch Cost Explorer**
4. 设置筛选条件：
   - **Service**: Amazon Bedrock
   - **Tag**: company
5. 选择 **Group by → Tag: company**
6. 即可看到按子公司分开的费用图表

### 导出报告

1. 在 Cost Explorer 中配置好筛选条件
2. 点击右上角 **Download CSV**
3. 可以按月导出给各子公司作为内部结算依据

---