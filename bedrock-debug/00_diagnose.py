"""
环境诊断脚本 —— 接 Bedrock 第一步跑这个。

检查项：
1. AWS 凭证是否有效
2. 当前 region 是否可达
3. 账号是否开通了目标模型的 access
4. 最小化 Converse 调用能否成功

用法：
    python 00_diagnose.py
    python 00_diagnose.py --region us-east-1 --model us.anthropic.claude-sonnet-4-5-20250929-v1:0
"""
import argparse
import os
import boto3
from botocore.exceptions import ClientError

from _common import (
    DEFAULT_MODEL_ID,
    DEFAULT_REGION,
    get_bedrock_control,
    get_bedrock_runtime,
    pretty_error,
    print_usage,
)


def check_credentials() -> bool:
    print("\n[1/4] 检查 AWS 凭证 ...")
    # Bedrock API Key 场景：不走 STS，直接标记通过
    if os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):
        print("   ✅ 检测到 AWS_BEARER_TOKEN_BEDROCK（Bedrock 专用 API Key）")
        print("   ℹ️  此模式下 sts:GetCallerIdentity 不可用，跳过身份验证")
        return True
    try:
        sts = boto3.client("sts")
        ident = sts.get_caller_identity()
        print(f"   ✅ Account: {ident['Account']}")
        print(f"   ✅ Arn    : {ident['Arn']}")
        return True
    except Exception as e:
        print(pretty_error(e))
        return False


def check_region(region: str) -> bool:
    print(f"\n[2/4] 检查 region '{region}' 的 Bedrock 可用性 ...")
    try:
        ctrl = get_bedrock_control(region)
        resp = ctrl.list_foundation_models()
        n = len(resp.get("modelSummaries", []))
        print(f"   ✅ 该 region 可见 {n} 个基础模型")
        return True
    except Exception as e:
        print(pretty_error(e))
        return False


def check_model_access(region: str, model_id: str) -> bool:
    print(f"\n[3/4] 检查模型访问权限: {model_id}")
    try:
        ctrl = get_bedrock_control(region)
        # inference profile（带 us./eu./au./global. 前缀）需要 list inference profiles
        prefix = model_id.split(".")[0] if "." in model_id else ""
        if prefix in ("us", "eu", "au", "apac", "global"):
            profiles = ctrl.list_inference_profiles().get("inferenceProfileSummaries", [])
            hit = [p for p in profiles if p["inferenceProfileId"] == model_id]
            if hit:
                print(f"   ✅ Inference profile 可见: {hit[0]['inferenceProfileName']}")
                print(f"      状态: {hit[0].get('status', 'N/A')}")
                return True
            else:
                print(f"   ⚠️  未在 inference profile 列表中找到 {model_id}")
                print(f"      可用 profile 示例：")
                for p in profiles[:5]:
                    print(f"        - {p['inferenceProfileId']}")
                return False
        else:
            # 基础模型 ID（不带区域前缀）
            resp = ctrl.get_foundation_model(modelIdentifier=model_id)
            print(f"   ✅ 找到基础模型: {resp['modelDetails']['modelName']}")
            return True
    except ClientError as e:
        print(pretty_error(e))
        return False


def check_converse(region: str, model_id: str) -> bool:
    print(f"\n[4/4] 最小化 Converse 调用测试 ...")
    try:
        client = get_bedrock_runtime(region)
        resp = client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": "ping"}]}],
            inferenceConfig={"maxTokens": 16, "temperature": 0.0},
        )
        text = resp["output"]["message"]["content"][0].get("text", "")
        print(f"   ✅ 调用成功。模型回复: {text[:80]!r}")
        print_usage(resp.get("usage", {}), prefix="   ")
        return True
    except Exception as e:
        print(pretty_error(e))
        return False


def main():
    ap = argparse.ArgumentParser(description="Bedrock 环境诊断")
    ap.add_argument("--region", default=DEFAULT_REGION)
    ap.add_argument("--model", default=DEFAULT_MODEL_ID)
    args = ap.parse_args()

    print("=" * 60)
    print(f"Bedrock 环境诊断")
    print(f"  region : {args.region}")
    print(f"  model  : {args.model}")
    print("=" * 60)

    results = [
        ("凭证", check_credentials()),
        ("Region", check_region(args.region)),
        ("模型权限", check_model_access(args.region, args.model)),
        ("Converse 调用", check_converse(args.region, args.model)),
    ]

    print("\n" + "=" * 60)
    print("诊断结果汇总")
    print("=" * 60)
    for name, ok in results:
        print(f"  {'✅' if ok else '❌'} {name}")

    if all(ok for _, ok in results):
        print("\n🎉 环境就绪，可以继续跑 01_basic_converse.py")
    else:
        print("\n⚠️  请先修复上面 ❌ 的项再继续。")


if __name__ == "__main__":
    main()
