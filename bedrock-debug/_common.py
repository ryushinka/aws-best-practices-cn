"""
公共工具：client 构造、模型 ID、错误美化输出。
所有 demo 脚本共享这个模块。
"""
import os
import sys
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError

# 默认 region（us-east-1 / us-west-2 都 OK，这两个是最主流的 Bedrock region）
DEFAULT_REGION = os.environ.get("AWS_REGION", "us-east-1")

# 默认模型：Claude Opus 4.6（2026-02 发布，当前旗舰）
# 新模型 ID 格式不再带 :0 后缀
# CRIS profile: us. / eu. / au. / global. 四种，US geo 覆盖 us-east-1/2, us-west-1/2, ca-central-1, ca-west-1
DEFAULT_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID",
    "us.anthropic.claude-opus-4-6-v1",
)


def get_bedrock_runtime(region: str = DEFAULT_REGION):
    """
    构造 bedrock-runtime client。
    - adaptive 重试：缓解 ThrottlingException
    - max_attempts=5：给突发限流留余地
    - read_timeout=300：长生成场景别被切
    """
    config = Config(
        region_name=region,
        retries={"mode": "adaptive", "max_attempts": 5},
        read_timeout=300,
        connect_timeout=10,
    )
    return boto3.client("bedrock-runtime", config=config)


def get_bedrock_control(region: str = DEFAULT_REGION):
    """control plane client：用于列模型、查 inference profile。"""
    return boto3.client("bedrock", region_name=region)


def pretty_error(e: Exception) -> str:
    """
    把 boto3 的 ClientError 解析成可读的中文诊断。
    """
    if isinstance(e, NoCredentialsError):
        return (
            "❌ 未找到 AWS 凭证。三种配置方式任选其一：\n"
            "   A) IAM access key（两个必须成对，只设 SECRET 无效）：\n"
            "      export AWS_ACCESS_KEY_ID=... && export AWS_SECRET_ACCESS_KEY=...\n"
            "   B) AWS Profile：aws configure --profile xxx && export AWS_PROFILE=xxx\n"
            "   C) Bedrock API Key（2025 新增，只要一个变量）：\n"
            "      export AWS_BEARER_TOKEN_BEDROCK=<console 生成>\n"
            "   验证：aws sts get-caller-identity"
        )

    if isinstance(e, ClientError):
        code = e.response.get("Error", {}).get("Code", "Unknown")
        msg = e.response.get("Error", {}).get("Message", str(e))

        hints = {
            "AccessDeniedException": (
                "模型未开通或 IAM 权限不够。\n"
                "   1) Bedrock console → Model access → Request access\n"
                "   2) IAM policy 需包含 bedrock:InvokeModel / InvokeModelWithResponseStream\n"
                "   3) Resource 需包含 inference-profile/* （用新模型时）"
            ),
            "ValidationException": (
                "请求参数校验失败。常见原因：\n"
                "   - temperature 和 topP 不能同时设置（Opus 4.6 / Sonnet 4.6 新约束，二选一）\n"
                "   - 新模型必须用 cross-region inference profile\n"
                "     modelId 前缀应为 us./eu./au./global.，例如 us.anthropic.claude-opus-4-6-v1\n"
                "   - Opus 4.6 / Sonnet 4.6 的 ID 不再带 :0 后缀，老格式会报错\n"
                "   - maxTokens 超过模型上限（Opus 4.6 上限 128K）\n"
                "   - messages 格式错误（role/content 结构）"
            ),
            "ThrottlingException": (
                "触发限流。\n"
                "   - 本脚本已开启 adaptive 重试，仍出现说明 QPS 过高\n"
                "   - 可申请提升 Bedrock service quota"
            ),
            "ResourceNotFoundException": (
                "modelId 或 region 错误。\n"
                f"   - 确认 region 是否支持该模型（当前 {DEFAULT_REGION}）\n"
                "   - 用 aws bedrock list-inference-profiles --region us-west-2 查询可用 ID"
            ),
            "UnrecognizedClientException": (
                "凭证无效或已过期。\n"
                "   - aws sts get-caller-identity 验证\n"
                "   - 检查 AWS_PROFILE 或环境变量"
            ),
            "ModelStreamErrorException": (
                "流式响应中断。通常是模型侧/网络问题，重试即可。"
            ),
        }
        hint = hints.get(code, "参考文档：https://docs.aws.amazon.com/bedrock/latest/userguide/")
        return f"❌ {code}: {msg}\n   → {hint}"

    return f"❌ {type(e).__name__}: {e}"


def print_usage(usage: dict, prefix: str = ""):
    """打印 token 用量（生产里应该上报到 CloudWatch EMF）。"""
    if not usage:
        return
    it = usage.get("inputTokens", 0)
    ot = usage.get("outputTokens", 0)
    tt = usage.get("totalTokens", it + ot)
    cache_read = usage.get("cacheReadInputTokens", 0)
    cache_write = usage.get("cacheWriteInputTokens", 0)
    line = f"{prefix}📊 usage: input={it}, output={ot}, total={tt}"
    if cache_read or cache_write:
        line += f", cache_read={cache_read}, cache_write={cache_write}"
    print(line)


def die(msg: str, code: int = 1):
    print(msg, file=sys.stderr)
    sys.exit(code)
