"""Course pack: the skill graph, micro-lessons and question bank, loaded from JSON files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


@dataclass(frozen=True)
class Skill:
    id: str
    name: str
    short: str
    group: str
    week: int
    hard: frozenset[str]
    soft: frozenset[str]
    effort: float
    x: int
    y: int


@dataclass(frozen=True)
class Item:
    id: str
    skill: str
    level: int
    prompt: str
    options: tuple[str, ...]
    answer: int
    why: str


@dataclass(frozen=True)
class CoursePack:
    id: str
    title: str
    source: str
    groups: tuple[dict, ...]
    skills: dict[str, Skill]
    lessons: dict[str, dict]
    items: dict[str, Item]
    items_by_skill: dict[str, tuple[Item, ...]]
    destinations: tuple[dict, ...]

    def hard_closure(self, targets: frozenset[str]) -> frozenset[str]:
        """The targets plus everything they depend on through hard prerequisites."""
        seen: set[str] = set()
        stack = list(targets)
        while stack:
            skill = stack.pop()
            if skill not in seen:
                seen.add(skill)
                stack.extend(self.skills[skill].hard)
        return frozenset(seen)


def load_pack(directory: Path = CONTENT_DIR) -> CoursePack:
    """Load and validate a course pack. Raises ValueError with a precise message when it is broken."""
    base = json.loads((directory / "skills.json").read_text(encoding="utf-8"))
    skills = {
        s["id"]: Skill(
            s["id"], s["name"], s["short"], s["group"], int(s["week"]),
            frozenset(s["hard"]), frozenset(s["soft"]), float(s["effort"]), int(s["x"]), int(s["y"]),
        )
        for s in base["skills"]
    }
    lessons: dict[str, dict] = {}
    items: dict[str, Item] = {}
    for part in sorted(directory.glob("part_*.json")):
        data = json.loads(part.read_text(encoding="utf-8"))
        for lesson in data["lessons"]:
            lessons[lesson["skill"]] = {k: lesson[k] for k in ("idea", "example", "trap")}
        for raw in data["items"]:
            item = Item(
                raw["id"], raw["skill"], int(raw["level"]), raw["prompt"],
                tuple(raw["options"]), int(raw["answer"]), raw["why"],
            )
            if item.id in items:
                raise ValueError(f"duplicate item id: {item.id}")
            items[item.id] = item

    _validate(skills, lessons, items, base["destinations"])
    by_skill = {
        sid: tuple(sorted((i for i in items.values() if i.skill == sid), key=lambda i: (i.level, i.id)))
        for sid in skills
    }
    return CoursePack(
        base["id"], base["title"], base["source"], tuple(base["groups"]),
        skills, lessons, items, by_skill, tuple(base["destinations"]),
    )


def _validate(skills: dict[str, Skill], lessons: dict, items: dict[str, Item], destinations: list[dict]) -> None:
    for skill in skills.values():
        for parent in skill.hard | skill.soft:
            if parent not in skills:
                raise ValueError(f"skill '{skill.id}' depends on unknown skill '{parent}'")
        if skill.id not in lessons:
            raise ValueError(f"skill '{skill.id}' has no lesson")
        if not any(i.skill == skill.id for i in items.values()):
            raise ValueError(f"skill '{skill.id}' has no questions")
    for item in items.values():
        if item.skill not in skills:
            raise ValueError(f"item '{item.id}' belongs to unknown skill '{item.skill}'")
        if len(item.options) < 2 or not 0 <= item.answer < len(item.options):
            raise ValueError(f"item '{item.id}' has an invalid answer key")
    for destination in destinations:
        for target in destination["targets"]:
            if target not in skills:
                raise ValueError(f"destination '{destination['id']}' targets unknown skill '{target}'")
    _check_acyclic(skills)


def _check_acyclic(skills: dict[str, Skill]) -> None:
    """Depth-first search for a cycle over hard and soft prerequisite edges."""
    white, grey, black = 0, 1, 2
    colour = dict.fromkeys(skills, white)

    def visit(skill_id: str) -> None:
        colour[skill_id] = grey
        for parent in skills[skill_id].hard | skills[skill_id].soft:
            if colour[parent] == grey:
                raise ValueError(f"prerequisite cycle through '{skill_id}' and '{parent}'")
            if colour[parent] == white:
                visit(parent)
        colour[skill_id] = black

    for skill_id in skills:
        if colour[skill_id] == white:
            visit(skill_id)
