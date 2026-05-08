"""
Tool Use / Function Calling —— 对应文档 §3。

完整的两轮对话流程：
    第 1 轮：user 提问 → 模型返回 stopReason="tool_use" + toolUse 块
    本地执行工具
    第 2 轮：把 toolResult 以 role="user" 回填 → 模型生成最终回答

关键点：
- tools 的 inputSchema 用 JSON Schema
- toolUse 块里有 toolUseId，回填时必须对应
- 可能一次返回多个 toolUse（并发工具调用），都要执行并回填

用法：
    python 03_tool_use.py
    python 03_tool_use.py --prompt "上海和北京今天天气怎么样？"
"""
import argparse
import json

from _common import DEFAULT_MODEL_ID, get_bedrock_runtime, pretty_error, print_usage


# -------- 工具定义 --------
TOOLS = [
    {
        "toolSpec": {
            "name": "get_weather",
            "description": "获取指定城市的当前天气。",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "城市中文名，例如 上海、北京",
                        },
                    },
                    "required": ["city"],
                }
            },
        }
    }
]


# -------- 本地工具实现（mock） --------
def tool_get_weather(city: str) -> dict:
    """真实场景这里调第三方 API；demo 用 mock。"""
    fake = {
        "上海": {"temp": 22, "condition": "多云", "humidity": 68},
        "北京": {"temp": 18, "condition": "晴", "humidity": 35},
        "深圳": {"temp": 27, "condition": "小雨", "humidity": 82},
    }
    return fake.get(city, {"temp": 20, "condition": "未知", "humidity": 50})


TOOL_DISPATCH = {
    "get_weather": lambda inp: tool_get_weather(inp["city"]),
}


def run(prompt: str, model_id: str):
    client = get_bedrock_runtime()
    messages = [{"role": "user", "content": [{"text": prompt}]}]

    # ========== 第 1 轮：模型决定是否调用工具 ==========
    print("─" * 60)
    print("第 1 轮：发送用户问题 + 工具清单")
    print("─" * 60)
    try:
        resp = client.converse(
            modelId=model_id,
            messages=messages,
            toolConfig={"tools": TOOLS},
            inferenceConfig={"maxTokens": 1024, "temperature": 0.2},
        )
    except Exception as e:
        print(pretty_error(e))
        return

    stop_reason = resp.get("stopReason")
    assistant_msg = resp["output"]["message"]
    print(f"stopReason: {stop_reason}")
    print_usage(resp.get("usage", {}))

    # 不需要调工具 → 直接结束
    if stop_reason != "tool_use":
        print("\n模型未请求工具，直接回答：")
        for block in assistant_msg["content"]:
            if "text" in block:
                print(block["text"])
        return

    # 把 assistant 的这条消息追加到历史
    messages.append(assistant_msg)

    # ========== 执行所有 toolUse ==========
    print("\n─" * 60)
    print("本地执行工具")
    print("─" * 60)
    tool_results = []
    for block in assistant_msg["content"]:
        if "toolUse" not in block:
            continue
        tu = block["toolUse"]
        name = tu["name"]
        tu_id = tu["toolUseId"]
        inp = tu["input"]
        print(f"🔧 {name}({json.dumps(inp, ensure_ascii=False)})  id={tu_id}")

        fn = TOOL_DISPATCH.get(name)
        if not fn:
            result = {"error": f"未知工具: {name}"}
            status = "error"
        else:
            try:
                result = fn(inp)
                status = "success"
            except Exception as e:
                result = {"error": str(e)}
                status = "error"

        print(f"   → {result}")
        tool_results.append(
            {
                "toolResult": {
                    "toolUseId": tu_id,
                    "content": [{"json": result}],
                    "status": status,
                }
            }
        )

    # ========== 第 2 轮：回填工具结果 ==========
    print("\n─" * 60)
    print("第 2 轮：回填 toolResult → 获取最终回答")
    print("─" * 60)
    messages.append({"role": "user", "content": tool_results})

    try:
        resp2 = client.converse(
            modelId=model_id,
            messages=messages,
            toolConfig={"tools": TOOLS},
            inferenceConfig={"maxTokens": 1024, "temperature": 0.2},
        )
    except Exception as e:
        print(pretty_error(e))
        return

    print(f"stopReason: {resp2.get('stopReason')}")
    print_usage(resp2.get("usage", {}))
    print("\n最终回答：")
    print("=" * 60)
    for block in resp2["output"]["message"]["content"]:
        if "text" in block:
            print(block["text"])
    print("=" * 60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default="上海今天天气怎么样？顺便也告诉我北京的。")
    ap.add_argument("--model", default=DEFAULT_MODEL_ID)
    args = ap.parse_args()
    run(args.prompt, args.model)


if __name__ == "__main__":
    main()
