import json
from typing import Callable
from langgraph.prebuilt import create_react_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from config import get_config
from tools import AGENT_TOOLS, execute_internal_tool


INTERNAL_COMMANDS = {
    "check system health": "system_health",
    "system health check": "system_health",
    "system health": "system_health",
    "health check": "system_health",
}


def create_agent():
    config = get_config()
    llm = ChatAnthropic(
        model=config.agent_model,
        api_key=config.anthropic_api_key,
        timeout=60.0,
    )
    return create_react_agent(llm, tools=AGENT_TOOLS)


def _parse_tool_output(content) -> tuple[dict, bool]:
    try:
        if isinstance(content, dict):
            return content, True
        if isinstance(content, str):
            return json.loads(content), True
        return {"result": content}, True
    except (json.JSONDecodeError, Exception):
        return {"error": str(content)}, False


def _build_messages(history: list[dict] | None, query: str) -> list:
    messages = []
    for msg in (history or []):
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=query))
    return messages


def _find_tool_input(messages: list, tool_call_id: str) -> dict:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc["id"] == tool_call_id:
                    return tc["args"]
    return {}


def _format_tool_name(name: str) -> str:
    return name.replace("_", " ").title()


def get_final_response(messages: list) -> str:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            return msg.content
    return ""


def _is_internal_command(query: str) -> str | None:
    normalized = query.strip().lower()
    for trigger, tool_name in INTERNAL_COMMANDS.items():
        if trigger in normalized:
            return tool_name
    return None


def _run_internal_command(tool_name: str) -> dict:
    try:
        result = execute_internal_tool(tool_name)
        return {
            "response": result.get("report", "Command executed successfully."),
            "tool_trace": [{"tool": tool_name, "input": {}, "output": result, "success": True}],
            "error": None,
        }
    except Exception as e:
        return {
            "response": f"Failed to execute {tool_name}: {e}",
            "tool_trace": [{"tool": tool_name, "input": {}, "output": None, "success": False}],
            "error": str(e),
        }


def run_agent(query: str, history: list[dict] | None = None) -> dict:
    return run_agent_with_progress(query, history, on_progress=None, on_tool=None)


class AgentRunner:
    PROGRESS_THINKING = 10
    PROGRESS_TOOLS_START = 20
    PROGRESS_TOOLS_MAX = 85
    PROGRESS_PER_TOOL = 15
    PROGRESS_SYNTHESIZING = 90
    PROGRESS_DONE = 100
    
    def __init__(self, on_progress=None, on_tool=None):
        self.on_progress = on_progress
        self.on_tool = on_tool
        self.tool_trace = []
        self.messages = []
        self.tools_started = 0
    
    def _tool_progress(self, tool_count: int) -> int:
        return min(self.PROGRESS_TOOLS_MAX, self.PROGRESS_TOOLS_START + tool_count * self.PROGRESS_PER_TOOL)
    
    def report(self, step: str, message: str, percent: int):
        if self.on_progress:
            self.on_progress(step, message, percent)
    
    def record_tool_result(self, msg: ToolMessage):
        output, success = _parse_tool_output(msg.content)
        tool_call = {
            "tool": msg.name,
            "input": _find_tool_input(self.messages, msg.tool_call_id),
            "output": output,
            "success": success,
        }
        self.tool_trace.append(tool_call)
        
        if self.on_tool:
            self.on_tool(tool_call)
        
        status = "completed" if success else "failed"
        self.report("tool", f"{_format_tool_name(msg.name)} {status}", self._tool_progress(len(self.tool_trace)))
    
    def handle_agent_event(self, event: dict):
        for msg in event.get("messages", []):
            self.messages.append(msg)
            
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    self.tools_started += 1
                    tool_name = _format_tool_name(tool_call["name"])
                    self.report("tool", f"Running {tool_name}...", self._tool_progress(self.tools_started))
    
    def handle_tools_event(self, event: dict):
        for msg in event.get("messages", []):
            self.messages.append(msg)
            
            if isinstance(msg, ToolMessage):
                self.record_tool_result(msg)
    
    def run(self, query: str, history: list[dict] | None = None) -> dict:
        internal_tool = _is_internal_command(query)
        if internal_tool:
            return self._run_internal(internal_tool)
        
        return self._run_agent(query, history)
    
    def _run_internal(self, tool_name: str) -> dict:
        self.report("tool", f"Running {tool_name}...", self._tool_progress(1))
        result = _run_internal_command(tool_name)
        
        if self.on_tool:
            self.on_tool(result["tool_trace"][0])
        
        self.report("done", "Complete", self.PROGRESS_DONE)
        return result
    
    def _run_agent(self, query: str, history: list[dict] | None) -> dict:
        self.report("thinking", "Analyzing your request...", self.PROGRESS_THINKING)
        
        agent = create_agent()
        self.messages = _build_messages(history, query)
        
        try:
            config = {"recursion_limit": 50} 
            for event in agent.stream({"messages": self.messages}, config=config):
                if "agent" in event:
                    self.handle_agent_event(event["agent"])
                if "tools" in event:
                    self.handle_tools_event(event["tools"])
            
            self.report("synthesizing", "Generating response...", self.PROGRESS_SYNTHESIZING)
            response = get_final_response(self.messages)
            self.report("done", "Complete", self.PROGRESS_DONE)
            
            return {"response": response, "tool_trace": self.tool_trace, "error": None}
        
        except Exception as e:
            self.report("error", str(e), 0)
            return {"response": f"An error occurred: {e}", "tool_trace": self.tool_trace, "error": str(e)}


def run_agent_with_progress(
    query: str, 
    history: list[dict] | None = None,
    on_progress: Callable[[str, str, int], None] | None = None,
    on_tool: Callable[[dict], None] | None = None,
) -> dict:
    runner = AgentRunner(on_progress=on_progress, on_tool=on_tool)
    return runner.run(query, history)
