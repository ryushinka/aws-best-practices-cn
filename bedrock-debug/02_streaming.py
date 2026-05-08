"""
流式输出 converse_stream —— 对应文档 §2。

为什么要用流式：
- Lambda / API Gateway 29 秒超时，长生成必须流式
- 前端实时打字机效果
- 更早感知错误（不用等整段生成完）

事件类型：
- messageStart / messageStop : 消息边界
- contentBlockStart / contentBlockDelta / contentBlockStop : 内容块
- metadata : 最后一条，包含 usage

用法：
    python 02_streaming.py
    python 02_streaming.py --prompt "写一首关于云的短诗"
"""
import argparse
import sys
import time

from _common import DEFAULT_MODEL_ID, get_bedrock_runtime, pretty_error, print_usage


def run(prompt: str, model_id: str):
    client = get_bedrock_runtime()

    try:
        stream = client.converse_stream(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 512, "temperature": 0.7},
        )
    except Exception as e:
        print(pretty_error(e))
        return

    print("=" * 60)
    t0 = time.time()
    first_token_t = None
    full_text = []
    usage = {}
    stop_reason = None

    try:
        for event in stream["stream"]:
            # 文本增量
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"].get("delta", {})
                chunk = delta.get("text", "")
                if chunk:
                    if first_token_t is None:
                        first_token_t = time.time()
                    full_text.append(chunk)
                    sys.stdout.write(chunk)
                    sys.stdout.flush()

            # 消息结束
            elif "messageStop" in event:
                stop_reason = event["messageStop"].get("stopReason")

            # 最后的 metadata（含 usage）
            elif "metadata" in event:
                usage = event["metadata"].get("usage", {})

            # 流式错误
            elif "internalServerException" in event or "modelStreamErrorException" in event:
                print(f"\n⚠️  流式错误: {event}")
    except Exception as e:
        print("\n" + pretty_error(e))
        return

    t1 = time.time()
    print("\n" + "=" * 60)
    print(f"stopReason   : {stop_reason}")
    print(f"⏱  total     : {(t1 - t0) * 1000:.0f} ms")
    if first_token_t:
        print(f"⏱  TTFT      : {(first_token_t - t0) * 1000:.0f} ms  (Time To First Token)")
    print_usage(usage)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default="写一首关于云的短诗，不超过4行。")
    ap.add_argument("--model", default=DEFAULT_MODEL_ID)
    args = ap.parse_args()
    run(args.prompt, args.model)


if __name__ == "__main__":
    main()
