"""In-process MCP server exposing the CSV tracker to the agents."""

from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from . import store

SERVER_NAME = "jobs"


def _text(text: str, is_error: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {"content": [{"type": "text", "text": text}]}
    if is_error:
        result["is_error"] = True
    return result


@tool(
    "already_tracked",
    "Check whether a job ad URL is already in the applications CSV. Call this before reading or writing anything for a job.",
    {"url": str},
)
async def already_tracked(args: dict[str, Any]) -> dict[str, Any]:
    tracked = store.is_tracked(args["url"])
    return _text("true - skip this job" if tracked else "false - new job")


@tool(
    "record_application",
    "Save the tailored cover letter and record the job in the applications CSV with status "
    "'ready_for_review'. This is the final 'send' step: the person reviews and submits it themselves.",
    {
        "type": "object",
        "properties": {
            "company": {"type": "string"},
            "role": {"type": "string", "description": "Job title as written in the ad"},
            "location": {"type": "string", "description": "City/region, country"},
            "work_mode": {"type": "string", "enum": store.WORK_MODES},
            "url": {"type": "string", "description": "Direct URL of the job ad"},
            "source": {"type": "string", "description": "Site the ad was found on, e.g. platsbanken, linkedin, company site"},
            "language": {"type": "string", "description": "Language of the ad and the letter, e.g. sv or en"},
            "deadline": {"type": "string", "description": "Application deadline (YYYY-MM-DD) or empty if unknown"},
            "apply_method": {"type": "string", "description": "How to apply: form URL, email address, or instructions"},
            "cover_letter": {"type": "string", "description": "Full cover letter text in Markdown"},
            "agent_id": {"type": "string", "description": "Your agent label, e.g. agent-1"},
            "notes": {"type": "string", "description": "Fit notes, gaps, or anything the person should know"},
        },
        "required": [
            "company", "role", "location", "work_mode", "url", "source",
            "language", "deadline", "apply_method", "cover_letter", "agent_id",
        ],
    },
)
async def record_application(args: dict[str, Any]) -> dict[str, Any]:
    try:
        row = await store.add_application(
            company=args["company"],
            role=args["role"],
            location=args["location"],
            work_mode=args["work_mode"],
            url=args["url"],
            source=args["source"],
            language=args["language"],
            deadline=args.get("deadline", ""),
            apply_method=args["apply_method"],
            cover_letter=args["cover_letter"],
            agent_id=args["agent_id"],
            notes=args.get("notes", ""),
        )
    except ValueError as e:
        return _text(str(e), is_error=True)
    return _text(f"Recorded {row['job_id']} ({row['company']} - {row['role']}), letter at {row['letter_path']}")


jobs_server = create_sdk_mcp_server(
    name=SERVER_NAME,
    tools=[already_tracked, record_application],
)

TOOL_NAMES = [f"mcp__{SERVER_NAME}__already_tracked", f"mcp__{SERVER_NAME}__record_application"]
