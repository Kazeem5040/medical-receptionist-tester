"""Completeness and consistency validation for scenario templates."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from .enums import SafetyClassification, ValidationSeverity
from .errors import ScenarioValidationIssue, ScenarioValidationResult
from .models import ScenarioTemplate
from .policies import DEFAULT_VALIDATION_POLICY, ScenarioValidationPolicy


def validate_scenario_template(
    template: ScenarioTemplate,
    policy: ScenarioValidationPolicy = DEFAULT_VALIDATION_POLICY,
) -> ScenarioValidationResult:
    """Validate a scenario template and return structured issues."""

    issues: list[ScenarioValidationIssue] = []

    _validate_identity(template, policy, issues)
    _validate_minimum_sections(template, policy, issues)
    _validate_unique_keys(template, issues)
    _validate_disclosure_rules(template, issues)
    _validate_safety(template, issues)
    _validate_termination_rules(template, policy, issues)
    _validate_variations(template, issues)

    return ScenarioValidationResult.from_issues(issues)


def _validate_identity(
    template: ScenarioTemplate,
    policy: ScenarioValidationPolicy,
    issues: list[ScenarioValidationIssue],
) -> None:
    if len(template.identity.tags) > policy.max_tags:
        issues.append(
            _issue(
                code="too_many_tags",
                message=f"Scenario has more than {policy.max_tags} tags.",
                path=("identity", "tags"),
            ),
        )

    duplicate_tags = _duplicates(template.identity.tags)
    for tag in duplicate_tags:
        issues.append(
            _issue(
                code="duplicate_tag",
                message=f"Duplicate scenario tag: {tag}.",
                path=("identity", "tags"),
            ),
        )

    if policy.require_synthetic_profile and not template.patient_profile.is_synthetic:
        issues.append(
            _issue(
                code="patient_profile_must_be_synthetic",
                message="Scenario patient profile must be synthetic.",
                path=("patient_profile", "is_synthetic"),
            ),
        )


def _validate_minimum_sections(
    template: ScenarioTemplate,
    policy: ScenarioValidationPolicy,
    issues: list[ScenarioValidationIssue],
) -> None:
    if len(template.objectives) < policy.min_objectives:
        issues.append(
            _issue(
                code="missing_objectives",
                message="Scenario must include at least one objective.",
                path=("objectives",),
            ),
        )

    if len(template.expected_behaviors) < policy.min_expected_behaviors:
        issues.append(
            _issue(
                code="missing_expected_behaviors",
                message="Scenario must include expected receptionist behavior.",
                path=("expected_behaviors",),
            ),
        )

    if len(template.evaluation_criteria) < policy.min_evaluation_criteria:
        issues.append(
            _issue(
                code="missing_evaluation_criteria",
                message="Scenario must include evaluation criteria.",
                path=("evaluation_criteria",),
            ),
        )

    if len(template.termination_rules) < policy.min_termination_rules:
        issues.append(
            _issue(
                code="missing_termination_rules",
                message="Scenario must include termination rules.",
                path=("termination_rules",),
            ),
        )


def _validate_unique_keys(
    template: ScenarioTemplate,
    issues: list[ScenarioValidationIssue],
) -> None:
    checks: tuple[tuple[str, Iterable[str], tuple[str, ...]], ...] = (
        ("duplicate_fact_key", (fact.key for fact in template.facts), ("facts",)),
        (
            "duplicate_objective_id",
            (objective.objective_id for objective in template.objectives),
            ("objectives",),
        ),
        (
            "duplicate_expectation_id",
            (
                expectation.expectation_id
                for expectation in template.expected_behaviors
            ),
            ("expected_behaviors",),
        ),
        (
            "duplicate_prohibited_id",
            (
                prohibited.prohibited_id
                for prohibited in template.prohibited_behaviors
            ),
            ("prohibited_behaviors",),
        ),
        (
            "duplicate_criterion_id",
            (criterion.criterion_id for criterion in template.evaluation_criteria),
            ("evaluation_criteria",),
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
    template: ScenarioTemplate,
    issues: list[ScenarioValidationIssue],
) -> None:
    fact_keys = {fact.key for fact in template.facts}
    disclosure_keys = [rule.fact_key for rule in template.disclosure_rules]

    for rule in template.disclosure_rules:
        if rule.fact_key not in fact_keys:
            issues.append(
                _issue(
                    code="disclosure_rule_unknown_fact",
                    message=f"Disclosure rule references unknown fact: {rule.fact_key}.",
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

    facts_with_rules = set(disclosure_keys)
    for fact in template.facts:
        if fact.required_for_objective and fact.key not in facts_with_rules:
            issues.append(
                _issue(
                    code="required_fact_missing_disclosure_rule",
                    message=(
                        f"Required fact '{fact.key}' must have a disclosure rule."
                    ),
                    path=("facts", fact.key),
                ),
            )


def _validate_safety(
    template: ScenarioTemplate,
    issues: list[ScenarioValidationIssue],
) -> None:
    if (
        template.safety.classification
        in {SafetyClassification.HIGH, SafetyClassification.EMERGENCY}
        and template.safety.escalation_instruction is None
    ):
        issues.append(
            _issue(
                code="missing_safety_escalation_instruction",
                message=(
                    "High-risk and emergency scenarios must include an "
                    "escalation instruction."
                ),
                path=("safety", "escalation_instruction"),
            ),
        )


def _validate_termination_rules(
    template: ScenarioTemplate,
    policy: ScenarioValidationPolicy,
    issues: list[ScenarioValidationIssue],
) -> None:
    has_duration_rule = False
    for index, rule in enumerate(template.termination_rules):
        if rule.max_call_seconds is None:
            continue

        has_duration_rule = True
        if rule.max_call_seconds > policy.max_call_seconds_limit:
            issues.append(
                _issue(
                    code="max_call_seconds_too_high",
                    message=(
                        f"Termination rule exceeds {policy.max_call_seconds_limit} "
                        "seconds."
                    ),
                    path=("termination_rules", index, "max_call_seconds"),
                ),
            )

    if template.termination_rules and not has_duration_rule:
        issues.append(
            _issue(
                code="missing_duration_termination_rule",
                message=(
                    "Scenario should include a max-duration termination rule "
                    "to prevent runaway calls."
                ),
                path=("termination_rules",),
                severity=ValidationSeverity.WARNING,
            ),
        )


def _validate_variations(
    template: ScenarioTemplate,
    issues: list[ScenarioValidationIssue],
) -> None:
    for duplicated_id in _duplicates(
        tuple(variation.variation_id for variation in template.variations),
    ):
        issues.append(
            _issue(
                code="duplicate_variation_id",
                message=f"Duplicate variation id: {duplicated_id}.",
                path=("variations", duplicated_id),
            ),
        )

    for variation in template.variations:
        for duplicated_option in _duplicates(
            tuple(option.option_id for option in variation.options),
        ):
            issues.append(
                _issue(
                    code="duplicate_variation_option_id",
                    message=(
                        f"Duplicate option id '{duplicated_option}' in variation "
                        f"'{variation.variation_id}'."
                    ),
                    path=("variations", variation.variation_id, "options"),
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
    severity: ValidationSeverity = ValidationSeverity.ERROR,
) -> ScenarioValidationIssue:
    return ScenarioValidationIssue(
        code=code,
        message=message,
        path=path,
        severity=severity,
    )
