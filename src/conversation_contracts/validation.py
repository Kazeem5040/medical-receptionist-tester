"""Validation for provider-independent conversation contracts."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from .enums import ContractValidationSeverity
from .errors import ContractValidationIssue, ContractValidationResult
from .models import ConversationContract
from .policies import DEFAULT_CONTRACT_POLICY, ConversationContractPolicy


def validate_conversation_contract(
    contract: ConversationContract,
    policy: ConversationContractPolicy = DEFAULT_CONTRACT_POLICY,
) -> ContractValidationResult:
    """Validate a conversation contract and return structured issues."""

    issues: list[ContractValidationIssue] = []

    if (
        policy.require_instance_fingerprint
        and contract.source.scenario_instance_fingerprint is None
    ):
        issues.append(
            _issue(
                code="missing_instance_fingerprint",
                message="Contract source must include a scenario instance fingerprint.",
                path=("source", "scenario_instance_fingerprint"),
            ),
        )

    if len(contract.objectives) < policy.min_objectives:
        issues.append(
            _issue(
                code="missing_objectives",
                message="Contract must include at least one patient objective.",
                path=("objectives",),
            ),
        )

    if len(contract.knowledge_boundaries) < policy.min_knowledge_boundaries:
        issues.append(
            _issue(
                code="missing_knowledge_boundaries",
                message="Contract must include knowledge boundaries.",
                path=("knowledge_boundaries",),
            ),
        )

    if len(contract.forbidden_behaviors) < policy.min_forbidden_behaviors:
        issues.append(
            _issue(
                code="missing_forbidden_behaviors",
                message="Contract must include forbidden patient behaviors.",
                path=("forbidden_behaviors",),
            ),
        )

    if len(contract.termination_rules) < policy.min_termination_rules:
        issues.append(
            _issue(
                code="missing_termination_rules",
                message="Contract must include termination rules.",
                path=("termination_rules",),
            ),
        )

    _validate_unique_ids(contract, issues)
    _validate_disclosure_rules(contract, issues)
    _validate_unknown_information(contract, issues)

    return ContractValidationResult.from_issues(issues)


def _validate_unique_ids(
    contract: ConversationContract,
    issues: list[ContractValidationIssue],
) -> None:
    checks: tuple[tuple[str, Iterable[str], tuple[str, ...]], ...] = (
        (
            "duplicate_objective_id",
            (objective.objective_id for objective in contract.objectives),
            ("objectives",),
        ),
        (
            "duplicate_milestone_id",
            (milestone.milestone_id for milestone in contract.milestones),
            ("milestones",),
        ),
        (
            "duplicate_recovery_rule_id",
            (rule.rule_id for rule in contract.recovery_rules),
            ("recovery_rules",),
        ),
        (
            "duplicate_clarification_rule_id",
            (rule.rule_id for rule in contract.clarification_rules),
            ("clarification_rules",),
        ),
        (
            "duplicate_steering_rule_id",
            (rule.rule_id for rule in contract.steering_rules),
            ("steering_rules",),
        ),
        (
            "duplicate_boundary_id",
            (boundary.boundary_id for boundary in contract.knowledge_boundaries),
            ("knowledge_boundaries",),
        ),
        (
            "duplicate_forbidden_behavior_id",
            (behavior.behavior_id for behavior in contract.forbidden_behaviors),
            ("forbidden_behaviors",),
        ),
    )

    for code, values, path in checks:
        for duplicated_value in _duplicates(tuple(values)):
            issues.append(
                _issue(
                    code=code,
                    message=f"Duplicate value: {duplicated_value}.",
                    path=path,
                ),
            )


def _validate_disclosure_rules(
    contract: ConversationContract,
    issues: list[ContractValidationIssue],
) -> None:
    known_fact_keys = {fact.key for fact in contract.known_information.facts}
    disclosure_keys = [rule.fact_key for rule in contract.disclosure_rules]

    for rule in contract.disclosure_rules:
        if rule.fact_key not in known_fact_keys:
            issues.append(
                _issue(
                    code="disclosure_rule_unknown_fact",
                    message=(
                        "Disclosure rule references a fact outside known "
                        f"information: {rule.fact_key}."
                    ),
                    path=("disclosure_rules", rule.fact_key),
                ),
            )

    for duplicated_key in _duplicates(disclosure_keys):
        issues.append(
            _issue(
                code="duplicate_disclosure_rule",
                message=f"Multiple disclosure rules exist for fact: {duplicated_key}.",
                path=("disclosure_rules", duplicated_key),
            ),
        )


def _validate_unknown_information(
    contract: ConversationContract,
    issues: list[ContractValidationIssue],
) -> None:
    unknown_topics = [item.topic.lower() for item in contract.unknown_information]
    if len(unknown_topics) != len(set(unknown_topics)):
        issues.append(
            _issue(
                code="duplicate_unknown_information_topic",
                message="Contract contains duplicate unknown information topics.",
                path=("unknown_information",),
                severity=ContractValidationSeverity.WARNING,
            ),
        )


def _duplicates(values: Iterable[str]) -> tuple[str, ...]:
    counts = Counter(values)
    return tuple(value for value, count in counts.items() if count > 1)


def _issue(
    *,
    code: str,
    message: str,
    path: tuple[str | int, ...],
    severity: ContractValidationSeverity = ContractValidationSeverity.ERROR,
) -> ContractValidationIssue:
    return ContractValidationIssue(
        code=code,
        message=message,
        path=path,
        severity=severity,
    )
