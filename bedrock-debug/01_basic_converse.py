"""
基础 Converse API 调用 —— 对应文档 §1。

展示要点：
- 使用 Converse（而非老的 InvokeModel）
- system / messages / inferenceConfig 三段式参数
- 解析返回的 text 和 usage

用法：
    python 01_basic_converse.py
    python 01_basic_converse.py --prompt "用一句话介绍 AWS Bedrock"
"""
import argparse
from _common import DEFAULT_MODEL_ID, get_bedrock_runtime, pretty_error, print_usage


def run(prompt: str, model_id: str):
    client = get_bedrock_runtime()

    try:
        resp = client.converse(
            modelId=model_id,
            messages=[
                {"role": "user", "content": [{"text": prompt}]},
            ],
            system=[{"text": "你是一个简洁的技术助手。回答尽量精炼。"}],
            inferenceConfig={
                "maxTokens": 1024,
                "temperature": 0.3,
                # 注意：Opus 4.6 / Sonnet 4.6 不允许 temperature 和 topP 同时设置
                # 二选一即可。想要更发散用 topP，需要严格确定性用 temperature=0
                # "topP": 0.9,
            },
        )
    except Exception as e:
        print(pretty_error(e))
        return

    # 输出
    msg = resp["output"]["message"]
    print("=" * 60)
    print(f"role: {msg['role']}")
    print("-" * 60)
    for block in msg["content"]:
        if "text" in block:
            print(block["text"])
    print("=" * 60)
    print(f"stopReason: {resp.get('stopReason')}")
    print_usage(resp.get("usage", {}))
    # 延迟信息（部分模型返回）
    metrics = resp.get("metrics", {})
    if metrics:
        print(f"⏱  latencyMs: {metrics.get('latencyMs')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default="用一句话介绍 AWS Bedrock")
    ap.add_argument("--model", default=DEFAULT_MODEL_ID)
    args = ap.parse_args()
    run(args.prompt, args.model)


if __name__ == "__main__":
    main()
