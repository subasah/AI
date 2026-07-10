from __future__ import annotations

from library.agents.base import ConfigurableAgent
from library.config.models import AgentConfig, SkillConfig, ToolConfig, VoiceAgentDeployment


def build_agents(
    deployment: VoiceAgentDeployment,
) -> dict[str, ConfigurableAgent]:
    """Instantiate all agents for a deployment from config."""
    tools_by_name = {t.name: t for t in deployment.tools}
    skills_by_id = {s.id: s for s in deployment.skills}
    agents: dict[str, ConfigurableAgent] = {}

    for agent_cfg in deployment.agents:
        skill_objs = [skills_by_id[sid] for sid in agent_cfg.skill_ids if sid in skills_by_id]
        tool_names = list(agent_cfg.tool_names)
        for skill in skill_objs:
            tool_names.extend(skill.tool_names)
        tool_objs = [tools_by_name[n] for n in dict.fromkeys(tool_names) if n in tools_by_name]
        agents[agent_cfg.id] = ConfigurableAgent(agent_cfg, skills=skill_objs, tools=tool_objs)

    return agents


def greeter_from_template(
    agent_id: str,
    company_name: str,
    brand_voice: str,
    handoff_targets: list[str],
) -> AgentConfig:
    return AgentConfig(
        id=agent_id,
        name="Greeter",
        role="Welcome callers and route intent",
        system_prompt=(
            f"You are the greeting agent for {company_name}. "
            f"Tone: {brand_voice}. Welcome the caller, learn their intent in one question, "
            "then transfer to the right specialist. Never invent business facts."
        ),
        entry_message=f"Thank you for calling {company_name}. How can I help you today?",
        handoff_targets=handoff_targets,
    )
