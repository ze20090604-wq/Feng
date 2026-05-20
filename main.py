import base64
import copy
import json
import os
import platform
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI


WORKSPACE = Path.cwd().resolve()
SESSION_PATH = WORKSPACE / "session.jsonl"
MEMORY_PATH = WORKSPACE / "memory" / "MEMORY.md"
TOKEN_BUDGET = int(os.getenv("TOKEN_BUDGET", "12000"))
MAX_REACT_STEPS = int(os.getenv("MAX_REACT_STEPS", "8"))


# WG-12: system prompt and runtime identity
def _runtime_env_note() -> str:
    sys_name = platform.system()
    shell_hint = (
        "exec 在 PowerShell 下執行；勿用 <<、heredoc、bash -c。"
        if os.name == "nt"
        else "exec 在系統 shell 下執行；多行腳本仍請 write_file 後 uv run。"
    )
    return (
        f"\n\n【執行環境】{sys_name}（os.name={os.name}）；專案根目錄為目前工作目錄。"
        f"{shell_hint}"
    )


def get_identity() -> str:
    """課堂人設：規則、顯示名、執行環境、exec 注意。"""
    system_text = "你是課堂程式助教，並請使用繁體中文。"
    nick = "法鬥超人"
    exec_note = (
        "\n\n【exec 注意】"
        "\n- 請依上方【執行環境】選擇相容的 shell 指令，勿假設為 Linux Bash。"
        "\n- 若要執行 Python：先用 write_file 寫入 .py，再 exec「uv run python 相對路徑」。"
    )
    tool_rule = (
        "\n\n【工具規則】"
        "\n- 需要計算、讀寫檔案、列目錄、局部修改檔案或執行命令時，必須呼叫工具，不可只憑空猜測。"
        "\n- 檔案操作請優先使用 read_file、write_file、edit_file、list_dir；shell 指令才使用 exec。"
        "\n- 使用圖片時，舊圖片只會以文字占位保留；只有本輪新附圖會送入 vision 模型。"
    )
    return (
        f"{system_text}\n\n【本場次顯示名稱】{nick}"
        f"{_runtime_env_note()}{exec_note}{tool_rule}"
    )


# WG-14: workspace-safe tools
def resolve_workspace_path(path: str | Path) -> Path:
    raw = Path(path)
    if raw.is_absolute():
        raise ValueError("Only relative paths inside the workspace are allowed.")
    resolved = (WORKSPACE / raw).resolve()
    if resolved != WORKSPACE and WORKSPACE not in resolved.parents:
        raise ValueError("Path escapes the workspace.")
    return resolved


@tool("read_file")
def read_file(path: str, start_line: int = 1, max_lines: int = 200) -> str:
    """Read a UTF-8 text file inside the workspace and return numbered lines."""
    try:
        target = resolve_workspace_path(path)
        if not target.is_file():
            return f"ERROR: not a file: {path}"
        lines = target.read_text(encoding="utf-8").splitlines()
        start = max(start_line, 1) - 1
        end = min(start + max(max_lines, 1), len(lines))
        return "\n".join(f"{i + 1}: {lines[i]}" for i in range(start, end))
    except Exception as exc:
        return f"ERROR: {exc}"


@tool("write_file")
def write_file(path: str, content: str) -> str:
    """Write UTF-8 text to a workspace file, creating parent directories."""
    try:
        target = resolve_workspace_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"OK: wrote {path} ({len(content)} chars)"
    except Exception as exc:
        return f"ERROR: {exc}"


@tool("edit_file")
def edit_file(path: str, old: str, new: str, count: int = 1) -> str:
    """Replace text in a workspace file. Use count=0 to replace every match."""
    try:
        target = resolve_workspace_path(path)
        if not target.is_file():
            return f"ERROR: not a file: {path}"
        text = target.read_text(encoding="utf-8")
        if old not in text:
            return "ERROR: old text not found"
        replace_count = -1 if count == 0 else max(count, 1)
        updated = text.replace(old, new, replace_count)
        target.write_text(updated, encoding="utf-8")
        return f"OK: edited {path}"
    except Exception as exc:
        return f"ERROR: {exc}"


@tool("list_dir")
def list_dir(path: str = ".") -> str:
    """List the first level of a workspace directory."""
    try:
        target = resolve_workspace_path(path)
        if not target.is_dir():
            return f"ERROR: not a directory: {path}"
        rows = []
        for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            kind = "dir " if child.is_dir() else "file"
            rows.append(f"{kind}\t{child.relative_to(WORKSPACE)}")
        return "\n".join(rows) or "(empty)"
    except Exception as exc:
        return f"ERROR: {exc}"


@tool("exec")
def exec_command(command: str, timeout_seconds: int = 30) -> str:
    """Run a single shell command in the workspace. Prefer file tools for file I/O."""
    try:
        result = subprocess.run(
            command,
            cwd=WORKSPACE,
            shell=True,
            text=True,
            capture_output=True,
            timeout=max(1, min(timeout_seconds, 120)),
        )
        output = (result.stdout or "") + (result.stderr or "")
        return f"exit_code={result.returncode}\n{output}".strip()
    except subprocess.TimeoutExpired:
        return "ERROR: command timed out"
    except Exception as exc:
        return f"ERROR: {exc}"


@tool
def add_numbers(a: float, b: float) -> float:
    """Add two numbers. Any request to add two numbers must call this tool."""
    return a + b


TOOLS: list[BaseTool] = [read_file, write_file, edit_file, list_dir, exec_command, add_numbers]
TOOL_MAP: dict[str, BaseTool] = {t.name: t for t in TOOLS}


# WG-15/16/21: JSONL persistence
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "\n".join(p for p in parts if p).strip()
    return str(content)


def user_row_dict(text: str, image_rel: str | None, media_type: str | None) -> dict[str, Any]:
    row: dict[str, Any] = {"role": "user", "content": text, "timestamp": now_iso()}
    if image_rel:
        row["image_path"] = image_rel
        if media_type:
            row["media_type"] = media_type
    return row


def serialize_message(message: BaseMessage) -> dict[str, Any] | None:
    if isinstance(message, HumanMessage):
        return {"role": "user", "content": content_to_text(message.content), "timestamp": now_iso()}
    if isinstance(message, AIMessage):
        row: dict[str, Any] = {
            "role": "assistant",
            "content": content_to_text(message.content),
            "timestamp": now_iso(),
        }
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            row["tool_calls"] = tool_calls
        return row
    if isinstance(message, ToolMessage):
        return {
            "role": "tool",
            "content": content_to_text(message.content),
            "tool_call_id": message.tool_call_id,
            "name": getattr(message, "name", None),
            "timestamp": now_iso(),
        }
    return None


def ensure_session_file(path: Path = SESSION_PATH) -> None:
    if path.exists():
        return
    meta = {
        "type": "metadata",
        "version": 1,
        "created_at": now_iso(),
        "note": "SystemMessage is intentionally not stored in JSONL.",
    }
    path.write_text(json.dumps(meta, ensure_ascii=False) + "\n", encoding="utf-8")


def append_session_rows(rows: list[dict[str, Any]], path: Path = SESSION_PATH) -> None:
    ensure_session_file(path)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_user_row_to_history_human(row: dict[str, Any]) -> HumanMessage:
    text = str(row.get("content", ""))
    image_rel = row.get("image_path")
    if not image_rel:
        return HumanMessage(content=text)
    media_type = row.get("media_type")
    placeholder = f"[此回合曾附圖，路徑：{image_rel}]"
    if media_type:
        placeholder += f"（media_type={media_type}）"
    return HumanMessage(content=f"{text}\n\n{placeholder}")


def load_session_jsonl(path: Path = SESSION_PATH) -> list[BaseMessage]:
    if not path.exists():
        return []

    history: list[BaseMessage] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            print(f"[warn] skip bad JSONL line {line_no}")
            continue

        role = row.get("role")
        if row.get("type") == "metadata":
            continue
        if role == "user":
            history.append(load_user_row_to_history_human(row))
        elif role == "assistant":
            history.append(AIMessage(content=row.get("content", ""), tool_calls=row.get("tool_calls") or []))
        elif role == "tool":
            history.append(
                ToolMessage(
                    content=row.get("content", ""),
                    tool_call_id=row.get("tool_call_id") or "unknown",
                    name=row.get("name"),
                )
            )
    return history


# WG-17/18/19: budget, transcript and long-term memory
def estimate_message_tokens(message: BaseMessage) -> int:
    text = content_to_text(message.content)
    tool_calls = getattr(message, "tool_calls", None)
    if tool_calls:
        text += json.dumps(tool_calls, ensure_ascii=False)
    return max(1, len(text) // 4 + 8)


def pick_consolidation_boundary(history: list[BaseMessage], budget: int = TOKEN_BUDGET) -> int:
    total = 0
    for index in range(len(history) - 1, -1, -1):
        total += estimate_message_tokens(history[index])
        if total > budget:
            for boundary in range(index + 1, len(history)):
                if isinstance(history[boundary], HumanMessage):
                    return boundary
            return min(index + 1, len(history))
    return 0


def trim_history_for_budget(history: list[BaseMessage], budget: int = TOKEN_BUDGET) -> list[BaseMessage]:
    boundary = pick_consolidation_boundary(history, budget)
    return history[boundary:]


def transcript_from_messages(messages: list[BaseMessage]) -> str:
    rows: list[str] = []
    for message in messages:
        if isinstance(message, HumanMessage):
            rows.append(f"User: {content_to_text(message.content)}")
        elif isinstance(message, AIMessage):
            rows.append(f"Assistant: {content_to_text(message.content)}")
            tool_calls = getattr(message, "tool_calls", None)
            if tool_calls:
                rows.append(f"Assistant tool_calls: {json.dumps(tool_calls, ensure_ascii=False)}")
        elif isinstance(message, ToolMessage):
            rows.append(f"Tool({message.tool_call_id}): {content_to_text(message.content)}")
    return "\n\n".join(rows)


def memory_block_for_system() -> str:
    if not MEMORY_PATH.exists():
        return ""
    text = MEMORY_PATH.read_text(encoding="utf-8").strip()
    if not text:
        return ""
    return f"# Long-term Memory\n\n{text}"


def maybe_consolidate_memory(llm: ChatOpenAI, history: list[BaseMessage]) -> None:
    if not history:
        return
    if sum(estimate_message_tokens(m) for m in history) <= TOKEN_BUDGET // 2:
        return

    boundary = pick_consolidation_boundary(history, TOKEN_BUDGET // 2)
    past = history[:boundary]
    if not past:
        return

    prompt = (
        "請把以下對話整理成可延續使用的長期記憶，保留使用者偏好、重要事實、待辦與決策。"
        "請使用繁體中文、條列、簡潔。\n\n"
        + transcript_from_messages(past)
    )
    try:
        response = llm.invoke([SystemMessage(content=get_identity()), HumanMessage(content=prompt)])
    except Exception as exc:
        print(f"[warn] memory consolidation failed: {exc}")
        return

    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_PATH.write_text(content_to_text(response.content).strip() + "\n", encoding="utf-8")


# WG-20: skills loader
@dataclass
class SkillEntry:
    name: str
    path: Path
    source: str
    description: str
    always: bool
    body: str


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        return {}, text

    meta: dict[str, str] = {}
    for raw in lines[1:end]:
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, "\n".join(lines[end + 1 :]).strip()


class SkillsLoader:
    def __init__(self, workspace: Path, builtin_skills_dir: Path) -> None:
        self.workspace_skills = workspace / "skills"
        self.builtin_skills = builtin_skills_dir

    def _entries_from_dir(self, root: Path, source: str, skip: set[str]) -> list[SkillEntry]:
        if not root.exists():
            return []
        entries: list[SkillEntry] = []
        for skill_dir in sorted(root.iterdir(), key=lambda p: p.name.lower()):
            skill_file = skill_dir / "SKILL.md"
            if not skill_dir.is_dir() or not skill_file.exists() or skill_dir.name in skip:
                continue
            text = skill_file.read_text(encoding="utf-8")
            meta, body = split_frontmatter(text)
            entries.append(
                SkillEntry(
                    name=skill_dir.name,
                    path=skill_file,
                    source=source,
                    description=meta.get("description") or skill_dir.name,
                    always=meta.get("always", "false").lower() == "true",
                    body=body,
                )
            )
        return entries

    def list_skills(self) -> list[SkillEntry]:
        workspace_entries = self._entries_from_dir(self.workspace_skills, "workspace", set())
        workspace_names = {entry.name for entry in workspace_entries}
        builtin_entries = self._entries_from_dir(self.builtin_skills, "builtin", workspace_names)
        return workspace_entries + builtin_entries

    def load_skill(self, name: str) -> str | None:
        for root in (self.workspace_skills, self.builtin_skills):
            path = root / name / "SKILL.md"
            if path.exists():
                return path.read_text(encoding="utf-8")
        return None


def build_skills_summary(entries: list[SkillEntry]) -> str:
    summarized = [entry for entry in entries if not entry.always]
    if not summarized:
        return ""
    return "\n".join(
        f"- {entry.name}: {entry.description} (`{entry.path.relative_to(WORKSPACE)}`)"
        for entry in summarized
    )


def build_system_prompt(loader: SkillsLoader) -> str:
    parts: list[str] = [get_identity()]
    memory = memory_block_for_system()
    if memory:
        parts.append(memory)

    entries = loader.list_skills()
    active = [entry for entry in entries if entry.always]
    if active:
        body = "\n\n---\n\n".join(f"### Skill: {entry.name}\n\n{entry.body}" for entry in active)
        parts.append(f"# Active Skills\n\n{body}")

    summary = build_skills_summary(entries)
    if summary:
        intro = (
            "可用 skills 如下。需要某項程序知識時，請先使用 read_file 讀取對應 SKILL.md，"
            "再依內容執行。"
        )
        parts.append(f"# Skills\n\n{intro}\n\n{summary}")
    return "\n\n---\n\n".join(parts)


# WG-21: image helpers and model-message preparation
def image_bytes_to_data_url(data: bytes, media_type: str) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def guess_media_type(path: Path, fallback: str = "image/png") -> str:
    ext = path.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    return fallback


def parse_user_input(raw: str) -> tuple[str, str | None]:
    if raw.startswith("/image "):
        rest = raw[len("/image ") :].strip()
        if not rest:
            return "", None
        parts = rest.split(maxsplit=1)
        image_rel = parts[0]
        text = parts[1] if len(parts) > 1 else input("圖片問題：").strip()
        return text, image_rel
    return raw, None


def build_human_message_for_current_turn(
    text: str, image_rel: str | None, project_root: Path = WORKSPACE
) -> tuple[HumanMessage, str | None, str | None]:
    if not image_rel:
        return HumanMessage(content=text), None, None

    try:
        full = resolve_workspace_path(image_rel)
    except Exception as exc:
        print(f"[warn] invalid image path: {exc}; sending text only.")
        return HumanMessage(content=text), None, None

    if not full.is_file():
        print(f"[warn] missing image for current turn: {image_rel}; sending text only.")
        return HumanMessage(content=text), None, None

    media_type = guess_media_type(full)
    with full.open("rb") as fh:
        data_url = image_bytes_to_data_url(fh.read(), media_type)

    return (
        HumanMessage(
            content=[
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": data_url}},
            ]
        ),
        str(Path(image_rel).as_posix()),
        media_type,
    )


def _human_to_text_only_placeholder(message: HumanMessage) -> HumanMessage:
    if isinstance(message.content, str):
        return message
    text = content_to_text(message.content) or "[此回合文字內容為空]"
    return HumanMessage(content=f"{text}\n\n[此回合曾附圖；歷史送模時已移除 image_url。]")


def messages_for_model(
    system_message: BaseMessage,
    history: list[BaseMessage],
    human_message: HumanMessage,
) -> list[BaseMessage]:
    out: list[BaseMessage] = [copy.deepcopy(system_message)]
    for message in history:
        copied = copy.deepcopy(message)
        if isinstance(copied, HumanMessage) and not isinstance(copied.content, str):
            copied = _human_to_text_only_placeholder(copied)
        out.append(copied)
    out.append(copy.deepcopy(human_message))
    return out


# WG-13: ReAct loop
def _normalize_tool_args(tool_call: dict[str, Any]) -> dict[str, Any]:
    args = tool_call.get("args", {})
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        try:
            parsed = json.loads(args)
            return parsed if isinstance(parsed, dict) else {"input": parsed}
        except json.JSONDecodeError:
            return {"input": args}
    return {"input": args}


def _stream_to_ai_message(llm_with_tools: Any, messages: list[BaseMessage]) -> AIMessage:
    accumulated = None
    for chunk in llm_with_tools.stream(messages):
        piece = content_to_text(chunk.content)
        if piece:
            print(piece, end="", flush=True)
        accumulated = chunk if accumulated is None else accumulated + chunk

    if accumulated is None:
        return AIMessage(content="")
    return AIMessage(
        content=accumulated.content or "",
        tool_calls=getattr(accumulated, "tool_calls", None) or [],
        invalid_tool_calls=getattr(accumulated, "invalid_tool_calls", None) or [],
    )


def run_react_turn(
    llm_with_tools: Any,
    system_message: SystemMessage,
    past: list[BaseMessage],
    human_message: HumanMessage,
) -> list[BaseMessage]:
    model_history = trim_history_for_budget(past)
    messages = messages_for_model(system_message, model_history, human_message)
    generated: list[BaseMessage] = []

    for _ in range(MAX_REACT_STEPS):
        response = _stream_to_ai_message(llm_with_tools, messages)
        generated.append(response)

        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            return generated

        messages.append(response)
        for call in tool_calls:
            name = call.get("name", "")
            call_id = call.get("id") or name or "tool-call"
            tool_obj = TOOL_MAP.get(name)
            if tool_obj is None:
                content = f"ERROR: unknown tool {name}"
            else:
                try:
                    content = str(tool_obj.invoke(_normalize_tool_args(call)))
                except Exception as exc:
                    content = f"ERROR: tool {name} failed: {exc}"
            tool_message = ToolMessage(content=content, tool_call_id=call_id, name=name)
            generated.append(tool_message)
            messages.append(tool_message)
        print("\n工具完成，繼續生成：", end="", flush=True)

    final = AIMessage(content="\n[warn] ReAct reached max steps before a final answer.")
    print(content_to_text(final.content), end="", flush=True)
    generated.append(final)
    return generated


def make_llm() -> ChatOpenAI | None:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_API_KEY")
    if not api_key:
        print("找不到 OPENAI_API_KEY（也未找到舊名 OPEN_API_KEY），請先在 .env 設定。")
        return None

    model = os.getenv("MODEL", "gpt-4o")
    base_url = os.getenv("BASE_URL") or None
    return ChatOpenAI(model=model, temperature=0.6, base_url=base_url, api_key=api_key)


def main() -> None:
    llm = make_llm()
    if llm is None:
        return

    loader = SkillsLoader(WORKSPACE, WORKSPACE / "builtin_skills")
    system_message = SystemMessage(content=build_system_prompt(loader))
    history: list[BaseMessage] = load_session_jsonl()
    llm_with_tools = llm.bind_tools(TOOLS)

    print("--- Agent 已啟動。輸入 exit/quit/bye 結束；附圖格式：/image 相對路徑 你的問題 ---")
    if history:
        print(f"[info] loaded {len(history)} history messages from {SESSION_PATH.name}")

    while True:
        raw = input("你：").strip()
        if raw.lower() in {"exit", "quit", "bye", "q"}:
            print("AI：再見，今天的對話已保存。")
            break
        if not raw:
            continue

        user_text, image_rel = parse_user_input(raw)
        if not user_text:
            continue

        human_message, stored_image_rel, media_type = build_human_message_for_current_turn(user_text, image_rel)
        history_human = load_user_row_to_history_human(
            user_row_dict(user_text, stored_image_rel, media_type)
        )

        try:
            print("AI：", end="", flush=True)
            generated = run_react_turn(llm_with_tools, system_message, history, human_message)
            print("\n")
        except Exception as exc:
            print(f"\n[error] model call failed: {exc}")
            continue

        new_messages = [history_human, *generated]
        history.extend(new_messages)

        rows = [user_row_dict(user_text, stored_image_rel, media_type)]
        rows.extend(row for row in (serialize_message(m) for m in generated) if row is not None)
        append_session_rows(rows)
        maybe_consolidate_memory(llm, history)


if __name__ == "__main__":
    main()
