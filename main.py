"""JobFinder: read the CV (context), then the lead runs N job-hunter subagents in parallel."""

import argparse
import asyncio
import json
import sys

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from jobfinder import config, prompts
from jobfinder.tools import SERVER_NAME, TOOL_NAMES, jobs_server

SUBAGENT_TOOLS = ["Read", "WebSearch", "WebFetch", *TOOL_NAMES]


# ---------- Phase 1: context ----------

async def build_profile() -> dict:
    print(f"Reading CV at {config.CV_PATH} ...")
    options = ClaudeAgentOptions(
        model=config.MODEL,
        cwd=str(config.ROOT),
        setting_sources=[],
        allowed_tools=["Read"],
        permission_mode="dontAsk",
        max_turns=10,
        output_format={"type": "json_schema", "schema": prompts.PROFILE_SCHEMA},
    )
    profile = None
    async for message in query(
        prompt=prompts.CONTEXT_PROMPT.format(cv_path=config.CV_PATH), options=options
    ):
        if isinstance(message, ResultMessage):
            if message.is_error or message.structured_output is None:
                raise RuntimeError(f"Could not build profile: {message.result or message.errors}")
            profile = message.structured_output
    return profile


def confirm_profile(profile: dict, ask: bool = True) -> dict:
    config.PROFILE_PATH.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n=== Profile ===")
    print(json.dumps(profile, indent=2, ensure_ascii=False))
    print(f"\nSaved to {config.PROFILE_PATH}.")
    if not ask:
        return profile
    answer = input("Press Enter to continue, edit the file first and then press Enter, or type q to quit: ")
    if answer.strip().lower() == "q":
        sys.exit(0)
    return json.loads(config.PROFILE_PATH.read_text(encoding="utf-8"))


# ---------- Phase 2: lead + job-hunters ----------

def _short(tool_input: dict) -> str:
    for key in ("query", "url", "company", "file_path", "description"):
        if key in tool_input:
            return f"{key}={str(tool_input[key])[:90]}"
    return ""


async def run_team(profile: dict, num_agents: int, jobs_per_agent: int) -> None:
    lead_prompt = prompts.LEAD_PROMPT.format(
        num_agents=num_agents,
        jobs_per_agent=jobs_per_agent,
        cv_path=config.CV_PATH,
        profile_path=config.PROFILE_PATH,
        profile_json=json.dumps(profile, indent=2, ensure_ascii=False),
    )
    options = ClaudeAgentOptions(
        model=config.MODEL,
        cwd=str(config.ROOT),
        setting_sources=[],
        system_prompt=lead_prompt,
        mcp_servers={SERVER_NAME: jobs_server},
        agents={
            "job-hunter": AgentDefinition(
                description=prompts.JOB_HUNTER_DESCRIPTION,
                prompt=prompts.JOB_HUNTER_PROMPT,
                tools=SUBAGENT_TOOLS,
                model=config.SUBAGENT_MODEL,
            )
        },
        allowed_tools=["Agent", *SUBAGENT_TOOLS],
        permission_mode="dontAsk",
        max_turns=config.MAX_TURNS,
        max_budget_usd=config.MAX_BUDGET_USD,
    )

    # Map each Agent tool call id to a readable label so subagent activity can be attributed.
    labels: dict[str, str] = {}
    async for message in query(prompt="Start the job search now.", options=options):
        if isinstance(message, AssistantMessage):
            who = labels.get(message.parent_tool_use_id, "lead") if message.parent_tool_use_id else "lead"
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    if block.name in ("Agent", "Task"):
                        labels[block.id] = block.input.get("description", f"agent-{len(labels) + 1}")
                        print(f"[lead] launching subagent: {labels[block.id]}")
                    else:
                        print(f"[{who}] {block.name.removeprefix(f'mcp__{SERVER_NAME}__')} {_short(block.input)}")
                elif isinstance(block, TextBlock) and who == "lead":
                    print(f"\n[lead] {block.text}\n")
        elif isinstance(message, ResultMessage):
            cost = f"${message.total_cost_usd:.2f}" if message.total_cost_usd is not None else "n/a"
            status = "error" if message.is_error else "done"
            print(f"\n=== {status} | turns: {message.num_turns} | cost: {cost} ===")
            if message.is_error and message.errors:
                print("\n".join(message.errors))


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-profile", action="store_true", help="re-read the CV even if profile.json exists")
    parser.add_argument("--profile-only", action="store_true", help="only run phase 1 (read the CV)")
    parser.add_argument("--agents", type=int, default=config.NUM_AGENTS)
    parser.add_argument("--jobs-per-agent", type=int, default=config.JOBS_PER_AGENT)
    parser.add_argument("--yes", action="store_true", help="don't ask to confirm the profile (used by the UI)")
    args = parser.parse_args()

    if args.refresh_profile or not config.PROFILE_PATH.exists():
        if not config.CV_PATH.exists():
            sys.exit(f"Put your CV at {config.CV_PATH} first.")
        profile = confirm_profile(await build_profile(), ask=not args.yes)
    else:
        profile = json.loads(config.PROFILE_PATH.read_text(encoding="utf-8"))
        print(f"Using existing profile {config.PROFILE_PATH} (pass --refresh-profile to re-read the CV).")

    if args.profile_only:
        return
    await run_team(profile, args.agents, args.jobs_per_agent)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main())
