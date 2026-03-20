"""
塔菲酱本地测试脚本
直接运行：python backend/Taffy/test_taffy.py
"""
import sys
import os
import json
import requests

# L50 API 配置
API_URL = "https://links-l50-pro.apps-sl.danlu.netease.com/api/v1/mcp_rag"


def build_payload(query: str, session_id: str, show_think: bool = False) -> dict:
    return {
        "query": query,
        "stream": True,
        "task_type": "l50",
        "session_id": session_id,
        "show_think_flag": show_think,
        "short_answer_flag": True,
        "image_list": []
    }


def chat(query: str, show_think: bool = False):
    import uuid
    session_id = f"test_{uuid.uuid4().hex[:8]}"
    payload = build_payload(query, session_id, show_think)
    headers = {"Content-Type": "application/json"}

    print(f"\n{'='*50}")
    print(f"问: {query}")
    print(f"{'='*50}")
    if show_think:
        print("[思考过程]")

    try:
        resp = requests.post(API_URL, json=payload, headers=headers, timeout=120, stream=True)
        resp.raise_for_status()

        in_think = False
        answer_started = False

        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue

            if line.startswith("think:"):
                content = line[len("think:"):]
                if show_think:
                    if not in_think:
                        in_think = True
                    print(f"  💭 {content}")

            elif line.startswith("data:"):
                content = line[len("data:"):]
                if content == "[DONE]":
                    print()
                    break
                try:
                    data = json.loads(content)
                    chunk = data.get("content", "")
                    if chunk:
                        if not answer_started:
                            if show_think:
                                print(f"\n[回答]")
                            answer_started = True
                        print(chunk, end="", flush=True)
                except json.JSONDecodeError:
                    if content:
                        print(content, end="", flush=True)

    except requests.exceptions.ConnectionError:
        print("❌ 连接失败，请确认在内网环境下运行")
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
    except Exception as e:
        print(f"❌ 错误: {e}")


def interactive_mode():
    """交互式对话模式"""
    print("🍬 塔菲酱本地测试")
    print("输入 /think 切换思考模式，输入 /quit 退出\n")

    show_think = False

    while True:
        try:
            user_input = input("你: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n再见！")
            break

        if not user_input:
            continue

        if user_input == "/quit":
            print("再见！")
            break

        if user_input == "/think":
            show_think = not show_think
            print(f"思考模式: {'开启 💭' if show_think else '关闭'}")
            continue

        chat(user_input, show_think)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 命令行直接传入问题
        query = " ".join(sys.argv[1:])
        show_think = "--think" in sys.argv
        chat(query.replace("--think", "").strip(), show_think)
    else:
        # 交互模式
        interactive_mode()
