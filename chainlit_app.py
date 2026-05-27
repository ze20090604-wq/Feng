import base64
import os
from typing import Any

import chainlit as cl
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
SUPPORTED_IMAGE_EXTENSIONS = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}


def _guess_image_mime(path: str, mime: str | None) -> str | None:
    if mime and mime.startswith("image/"):
        return mime
    extension = os.path.splitext(path)[1].lower()
    return SUPPORTED_IMAGE_EXTENSIONS.get(extension)


def _build_user_content(message: str, elements: list[Any]) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = []

    if message.strip():
        content.append({"type": "text", "text": message})

    for element in elements:
        path = getattr(element, "path", None)
        if not path:
            continue

        guessed_mime = _guess_image_mime(path, getattr(element, "mime", None))
        if not guessed_mime:
            continue

        with open(path, "rb") as f:
            image_bytes = f.read()

        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{guessed_mime};base64,{base64_image}"
                },
            }
        )

    return content if content else [{"type": "text", "text": ""}]


@cl.on_chat_start
async def on_chat_start() -> None:
    cl.user_session.set("history", [])
    await cl.Message(
        content="你好，我已準備好聊天。你也可以直接上傳圖片，我會一併帶入模型。"
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    history = cl.user_session.get("history") or []
    user_content = _build_user_content(message.content, message.elements or [])
    history.append({"role": "user", "content": user_content})

    response_msg = cl.Message(content="")
    await response_msg.send()

    collected_text = ""
    stream = await client.chat.completions.create(
        model=MODEL,
        messages=history,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta
        token = delta.content or ""
        if token:
            collected_text += token
            await response_msg.stream_token(token)

    history.append({"role": "assistant", "content": collected_text})
    cl.user_session.set("history", history)
    await response_msg.update()
