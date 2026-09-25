"""Skill helpers — cluster tools + sub-prompt for an agent."""

from __future__ import annotations

from library.config.models import SkillConfig, ToolConfig


def tools_for_skill(skill: SkillConfig, catalog: list[ToolConfig]) -> list[ToolConfig]:
    wanted = set(skill.tool_names)
    return [t for t in catalog if t.name in wanted]
