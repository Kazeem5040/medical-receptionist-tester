from __future__ import annotations

from tests.vapi_adapter_factories import conversation_contract
from vapi_adapter.instructions import build_vapi_system_instruction


def test_instruction_sections_are_present() -> None:
    instructions = build_vapi_system_instruction(conversation_contract())

    assert "# Role" in instructions
    assert "# Patient Identity" in instructions
    assert "# Patient Objectives" in instructions
    assert "# Disclosure Rules" in instructions
    assert "# Forbidden Behaviors" in instructions


def test_instructions_preserve_principles_not_exact_scripts() -> None:
    instructions = build_vapi_system_instruction(conversation_contract())

    assert "not exact sentences to recite" in instructions
    assert "Say:" not in instructions
    assert "verbatim" not in instructions.lower()
