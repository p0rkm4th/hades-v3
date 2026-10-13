"""Strict translation from OpenAI chat messages to Ollama's native chat schema."""
from __future__ import annotations

import json


class ProtocolError(ValueError):
    """The request cannot be represented by the native Ollama chat contract."""


_NATIVE_MESSAGE_FIELDS = {
    "role", "content", "thinking", "images", "tool_calls", "tool_name", "tool_call_id",
}


def translate_messages(messages: list[dict]) -> list[dict]:
    """Translate OpenAI tool-history fields without dropping content or associations."""
    if not isinstance(messages, list) or not messages:
        raise ProtocolError("messages must be a nonempty array")
    output: list[dict] = []
    pending: dict[str, str] = {}

    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            raise ProtocolError(f"messages[{index}] must be an object")
        role = message.get("role")
        if role not in {"system", "developer", "user", "assistant", "tool"}:
            raise ProtocolError(f"messages[{index}].role is unsupported")
        if pending and role != "tool":
            raise ProtocolError("every assistant tool call must have its associated tool result before the next message")
        allowed_fields = {
            "assistant": {"role", "content", "tool_calls", "refusal", "function_call", "reasoning_content", "thinking"},
            "tool": {"role", "content", "tool_call_id", "name"},
            "system": {"role", "content"},
            "developer": {"role", "content"},
            "user": {"role", "content"},
        }[role]
        if set(message) - allowed_fields:
            raise ProtocolError(f"messages[{index}] contains unsupported fields")

        native = {"role": "system" if role == "developer" else role}
        content = message.get("content", "")
        if content is None and role == "assistant":
            content = ""
        if not isinstance(content, str):
            raise ProtocolError(f"messages[{index}].content must be a string; multipart content is unsupported")
        native["content"] = content

        if role == "assistant":
            if "refusal" in message and message["refusal"] not in (None, ""):
                raise ProtocolError("assistant refusal field has no lossless Ollama mapping")
            if message.get("function_call") is not None:
                raise ProtocolError("legacy function_call history is unsupported; use tool_calls")
            if "reasoning_content" in message:
                reasoning = message["reasoning_content"]
                if not isinstance(reasoning, str):
                    raise ProtocolError(f"messages[{index}].reasoning_content must be a string")
                native["thinking"] = reasoning
            elif "thinking" in message:
                if not isinstance(message["thinking"], str):
                    raise ProtocolError(f"messages[{index}].thinking must be a string")
                native["thinking"] = message["thinking"]
            calls = message.get("tool_calls", [])
            if not isinstance(calls, list):
                raise ProtocolError(f"messages[{index}].tool_calls must be an array")
            if calls:
                translated_calls = []
                for call_index, call in enumerate(calls):
                    prefix = f"messages[{index}].tool_calls[{call_index}]"
                    if not isinstance(call, dict) or call.get("type") != "function":
                        raise ProtocolError(f"{prefix} must be a function tool call")
                    call_id = call.get("id")
                    function = call.get("function")
                    if not isinstance(call_id, str) or not call_id or call_id in pending:
                        raise ProtocolError(f"{prefix}.id must be a unique nonempty string")
                    if not isinstance(function, dict) or not isinstance(function.get("name"), str) or not function["name"]:
                        raise ProtocolError(f"{prefix}.function.name is required")
                    raw_arguments = function.get("arguments")
                    if not isinstance(raw_arguments, str):
                        raise ProtocolError(f"{prefix}.function.arguments must use the OpenAI JSON-string form")
                    try:
                        arguments = json.loads(raw_arguments)
                    except json.JSONDecodeError as exc:
                        raise ProtocolError(f"{prefix}.function.arguments is invalid JSON") from exc
                    if not isinstance(arguments, dict):
                        raise ProtocolError(f"{prefix}.function.arguments must encode an object")
                    unknown_call_fields = set(call) - {"id", "type", "function"}
                    unknown_function_fields = set(function) - {"name", "arguments"}
                    if unknown_call_fields or unknown_function_fields:
                        raise ProtocolError(f"{prefix} contains fields with no lossless Ollama mapping")
                    translated_calls.append({
                        "id": call_id,
                        "function": {"name": function["name"], "arguments": arguments},
                    })
                    pending[call_id] = function["name"]
                native["tool_calls"] = translated_calls
        elif role == "tool":
            call_id = message.get("tool_call_id")
            if not isinstance(call_id, str) or call_id not in pending:
                raise ProtocolError(f"messages[{index}] has no matching outstanding tool_call_id")
            name = message.get("name") or pending[call_id]
            if name != pending[call_id]:
                raise ProtocolError(f"messages[{index}].name does not match its tool_call_id")
            native["tool_call_id"] = call_id
            native["tool_name"] = name
            del pending[call_id]
        else:
            if "name" in message:
                raise ProtocolError(f"messages[{index}].name has no lossless Ollama mapping")

        if not set(native) <= _NATIVE_MESSAGE_FIELDS:
            raise ProtocolError(f"messages[{index}] could not be represented natively")
        output.append(native)

    if pending:
        raise ProtocolError("assistant tool calls are missing their tool results")
    return output


def translate_tools(tools: list[dict] | None) -> list[dict] | None:
    """Convert OpenAI tool declarations while rejecting unsupported semantics."""
    if tools is None:
        return None
    if not isinstance(tools, list):
        raise ProtocolError("tools must be an array")
    output = []
    for index, tool in enumerate(tools):
        if not isinstance(tool, dict) or set(tool) != {"type", "function"} or tool.get("type") != "function":
            raise ProtocolError(f"tools[{index}] must be an OpenAI function tool")
        function = tool["function"]
        if not isinstance(function, dict):
            raise ProtocolError(f"tools[{index}].function must be an object")
        if set(function) - {"name", "description", "parameters", "strict"}:
            raise ProtocolError(f"tools[{index}].function contains unsupported fields")
        if function.get("strict") not in (None, False):
            raise ProtocolError(f"tools[{index}].function.strict cannot be represented by Ollama")
        if not isinstance(function.get("name"), str) or not function["name"]:
            raise ProtocolError(f"tools[{index}].function.name is required")
        if not isinstance(function.get("parameters"), dict):
            raise ProtocolError(f"tools[{index}].function.parameters must be a JSON Schema object")
        native_function = {key: function[key] for key in ("name", "description", "parameters") if key in function}
        output.append({"type": "function", "function": native_function})
    return output


def validate_native_tool_history(messages: list[dict]) -> None:
    """Validate a native history independently, as a strict Ollama test peer would."""
    if not isinstance(messages, list) or not messages:
        raise ProtocolError("messages must be a nonempty array")
    pending: dict[str, str] = {}
    for index, message in enumerate(messages):
        if not isinstance(message, dict) or set(message) - _NATIVE_MESSAGE_FIELDS:
            raise ProtocolError(f"messages[{index}] is not a native Ollama message")
        role = message.get("role")
        if role not in {"system", "user", "assistant", "tool"}:
            raise ProtocolError(f"messages[{index}].role is not a native Ollama role")
        if not isinstance(message.get("content", ""), str):
            raise ProtocolError(f"messages[{index}].content must be a string")
        if pending and role != "tool":
            raise ProtocolError("native history moved past unresolved tool calls")
        if role == "assistant":
            calls = message.get("tool_calls", [])
            if not isinstance(calls, list):
                raise ProtocolError(f"messages[{index}].tool_calls must be an array")
            for call in calls:
                if not isinstance(call, dict):
                    raise ProtocolError(f"messages[{index}].tool_calls contains a non-object")
                call_id = call.get("id")
                function = call.get("function") or {}
                if (not isinstance(call_id, str) or not call_id or call_id in pending
                        or not isinstance(function, dict)
                        or not isinstance(function.get("name"), str)
                        or not isinstance(function.get("arguments"), dict)):
                    raise ProtocolError("native assistant tool call is malformed")
                pending[call_id] = function["name"]
        elif role == "tool":
            call_id = message.get("tool_call_id")
            if (not isinstance(call_id, str) or call_id not in pending
                    or message.get("tool_name") != pending[call_id]):
                raise ProtocolError("native tool result lacks a matching id and tool_name")
            del pending[call_id]
    if pending:
        raise ProtocolError("native tool calls are missing results")
