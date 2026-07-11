"""Instruction assembly for Vapi model.messages.

This module converts a ConversationContract into provider-facing instructions
without turning the patient into a rigid script.
"""

from __future__ import annotations

from conversation_contracts import ConversationContract


def build_vapi_system_instruction(contract: ConversationContract) -> str:
    """Build deterministic Vapi system instructions from a contract."""

    sections = [     
        _section(
            "Role",
            (
                "You are the synthetic patient for a medical AI receptionist "
                "test call. Behave like the patient described below. Do not act "
                "as a tester, evaluator, developer, or assistant."
            ),
        ),
        _patient_identity(contract),
        _objectives(contract),
        _conversation_style(contract),
        _known_information(contract),
        _unknown_information(contract),
        _disclosure_rules(contract),
        _milestones(contract),
        _recovery_rules(contract),
        _clarification_rules(contract),
        _steering_rules(contract),
        _termination_rules(contract),
        _safety(contract),
        _behavioral_constraints(contract),
        _knowledge_boundaries(contract),
        _forbidden_behaviors(contract),
        _section(
            "Natural Conversation Rule",
            (
                "Use natural, varied language. The contract defines principles "
                "and boundaries, not exact sentences to recite."
            ),
        ),
    ]
    return "\n\n".join(section for section in sections if section)


def represented_contract_sections() -> tuple[str, ...]:
    """Return contract sections intentionally represented in instructions."""

    return (
        "patient_identity",
        "objectives",
        "known_information",
        "unknown_information",
        "disclosure_rules",
        "conversation_style",
        "milestones",
        "recovery_rules",
        "clarification_rules",
        "steering_rules",
        "termination_rules",
        "safety_instruction",
        "behavioral_constraints",
        "knowledge_boundaries",
        "forbidden_behaviors",
    )


def _patient_identity(contract: ConversationContract) -> str:
    identity = contract.patient_identity
    details = [
        f"Name: {identity.given_name} {identity.family_name}",
    ]
    if identity.birth_date is not None:
        details.append(f"Birth date: {identity.birth_date.isoformat()}")
    if identity.pronouns is not None:
        details.append(f"Pronouns: {identity.pronouns}")
    if identity.insurance_name is not None:
        details.append(f"Insurance: {identity.insurance_name}")
    if identity.member_id is not None:
        details.append(f"Member ID: {identity.member_id}")
    if identity.phone_number is not None:
        details.append(f"Callback phone: {identity.phone_number}")
    if identity.notes is not None:
        details.append(f"Notes: {identity.notes}")
    return _section("Patient Identity", _bullets(details))


def _objectives(contract: ConversationContract) -> str:
    lines = [
        (
            f"{objective.priority}: {objective.title} — "
            f"{objective.description} Success means: {objective.success_condition}"
        )
        for objective in contract.objectives
    ]
    return _section("Patient Objectives", _bullets(lines))


def _conversation_style(contract: ConversationContract) -> str:
    style = contract.conversation_style
    lines = [
        f"Persona: {style.persona}",
        f"Personality: {style.personality}",
        f"Tone: {style.tone}",
        f"Pacing: {style.pacing}",
        f"Cooperation: {style.cooperation_level}",
        f"Interruptions allowed: {style.should_interrupt}",
    ]
    if style.steering_notes is not None:
        lines.append(f"Scenario steering notes: {style.steering_notes}")
    return _section("Conversation Style", _bullets(lines))


def _known_information(contract: ConversationContract) -> str:
    facts = contract.known_information.facts
    if not facts:
        return _section(
            "Known Information",
            "No scenario facts were provided. Do not invent patient facts.",
        )
    return _section(
        "Known Information",
        _bullets(
            [
                (
                    f"{fact.key}: {fact.value} "
                    f"(sensitivity: {fact.sensitivity}, "
                    f"required: {fact.required_for_objective})"
                )
                for fact in facts
            ],
        ),
    )


def _unknown_information(contract: ConversationContract) -> str:
    return _section(
        "Unknown Information",
        _bullets(
            [
                f"{item.topic}: {item.behavior} Reason: {item.reason}"
                for item in contract.unknown_information
            ],
        ),
    )


def _disclosure_rules(contract: ConversationContract) -> str:
    return _section(
        "Disclosure Rules",
        _bullets(
            [
                (
                    f"{rule.fact_key}: timing={rule.timing}. "
                    f"Behavior: {rule.behavior}"
                )
                for rule in contract.disclosure_rules
            ],
        ),
    )


def _milestones(contract: ConversationContract) -> str:
    return _section(
        "Conversation Milestones",
        _bullets(
            [
                f"{milestone.milestone_type}: {milestone.description}"
                for milestone in contract.milestones
            ],
        ),
    )


def _recovery_rules(contract: ConversationContract) -> str:
    return _section(
        "Recovery Behavior",
        _bullets(
            [
                f"When {rule.trigger}: {rule.behavior}"
                for rule in contract.recovery_rules
            ],
        ),
    )


def _clarification_rules(contract: ConversationContract) -> str:
    return _section(
        "Clarification Behavior",
        _bullets(
            [
                f"When {rule.trigger}: {rule.behavior}"
                for rule in contract.clarification_rules
            ],
        ),
    )


def _steering_rules(contract: ConversationContract) -> str:
    return _section(
        "Steering Behavior",
        _bullets(
            [
                f"When {rule.trigger}: {rule.behavior}"
                for rule in contract.steering_rules
            ],
        ),
    )


def _termination_rules(contract: ConversationContract) -> str:
    return _section(
        "Termination Behavior",
        _bullets(
            [
                f"{rule.reason}: {rule.condition}"
                for rule in contract.termination_rules
            ],
        ),
    )


def _safety(contract: ConversationContract) -> str:
    safety = contract.safety_instruction
    lines = [
        f"Classification: {safety.classification}",
        f"Instruction: {safety.instruction}",
    ]
    if safety.emergency_keywords:
        lines.append(f"Emergency keywords: {', '.join(safety.emergency_keywords)}")
    return _section("Safety", _bullets(lines))


def _behavioral_constraints(contract: ConversationContract) -> str:
    return _section(
        "Behavioral Constraints",
        _bullets(
            [
                f"{constraint.severity}: {constraint.rule}"
                for constraint in contract.behavioral_constraints
            ],
        ),
    )


def _knowledge_boundaries(contract: ConversationContract) -> str:
    return _section(
        "Knowledge Boundaries",
        _bullets(
            [
                (
                    f"{boundary.boundary_type}: {boundary.rule} "
                    f"Reason: {boundary.reason}"
                )
                for boundary in contract.knowledge_boundaries
            ],
        ),
    )


def _forbidden_behaviors(contract: ConversationContract) -> str:
    return _section(
        "Forbidden Behaviors",
        _bullets(
            [
                f"{behavior.severity}: {behavior.behavior}. Reason: {behavior.reason}"
                for behavior in contract.forbidden_behaviors
            ],
        ),
    )


def _section(title: str, body: str) -> str:
    if not body:
        return ""
    return f"# {title}\n{body}"


def _bullets(lines: list[str]) -> str:
    return "\n".join(f"- {line}" for line in lines if line)
