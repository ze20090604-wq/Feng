from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

import chainlit as cl

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_core import Agent


DONE = object()


async def _get_agent() -> Agent | None:
    agent = cl.user_session.get("agent")
    if isinstance(agent, Agent):
        return agent

    try:
        agent = await asyncio.to_thread(Agent.from_env)
    except RuntimeError as exc:
        await cl.Message(content=f"啟動失敗：{exc}").send()
        return None

    cl.user_session.set("agent", agent)
    return agent


@cl.on_chat_start
async def start() -> None:
    agent = await _get_agent()
    if agent is None:
        return

    if agent.history:
        status = (
            f"已載入 {len(agent.history)} 則歷史訊息，"
            f"last_consolidated={agent.last_consolidated}。"
        )
    else:
        status = "已建立新的對話。"

    await cl.Message(
        content=(
            "法鬥超人 UI 已就緒。\n\n"
            f"{status}\n\n"
            "直接輸入訊息即可開始聊天。"
        )
    ).send()


@cl.on_message
async def main(message: cl.Message) -> None:
    agent = await _get_agent()
    if agent is None:
        return

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[Any] = asyncio.Queue()
    assistant_message = cl.Message(content="")
    streamed_text = ""

    await assistant_message.send()

    def on_token(token: str) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, token)

    def run_agent() -> None:
        try:
            final_text = agent.chat(message.content, on_token=on_token)
            loop.call_soon_threadsafe(queue.put_nowait, (DONE, final_text, None))
        except Exception as exc:
            loop.call_soon_threadsafe(queue.put_nowait, (DONE, "", exc))

    worker = asyncio.create_task(asyncio.to_thread(run_agent))

    while True:
        item = await queue.get()
        if isinstance(item, tuple) and item and item[0] is DONE:
            _, final_text, error = item
            if error is not None:
                assistant_message.content = f"發生錯誤：{error}"
                await assistant_message.update()
            else:
                if not streamed_text and final_text:
                    streamed_text = final_text
                assistant_message.content = streamed_text
                await assistant_message.update()
            break

        token = str(item)
        streamed_text += token
        await assistant_message.stream_token(token)

    await worker
