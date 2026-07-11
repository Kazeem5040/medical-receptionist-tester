from __future__ import annotations

from scenarios import (
    DisclosureRule,
    DisclosureTiming,
    EvaluationCriterion,
    EvaluationCriterionType,
    ExpectedReceptionistBehavior,
    PatientFact,
    SafetyClassification,
    SafetyPolicy,
    ScenarioCategory,
    ScenarioIdentity,
    ScenarioLifecycle,
    ScenarioManager,
    ScenarioObjective,
    ScenarioTemplate,
    SyntheticPatientProfile,
    TerminationReason,
    TerminationRule,
)


def test_valid_template_has_no_validation_errors() -> None:
    result = ScenarioManager().validate_template(_valid_template())

    assert result.is_valid
    assert result.errors == ()


def test_required_fact_without_disclosure_rule_is_error() -> None:
    template = _valid_template().model_copy(update={"disclosure_rules": ()})

    result = ScenarioManager().validate_template(template)

    assert not result.is_valid
    assert {issue.code for issue in result.errors} == {
        "required_fact_missing_disclosure_rule",
    }


def test_unknown_disclosure_fact_is_error() -> None:
    template = _valid_template().model_copy(
        update={
            "disclosure_rules": (
                DisclosureRule(
                    fact_key="unknown-fact",
                    timing=DisclosureTiming.WHEN_ASKED,
                ),
            ),
        },
    )

    result = ScenarioManager().validate_template(template)

    assert not result.is_valid
    assert "disclosure_rule_unknown_fact" in {issue.code for issue in result.errors}


def test_high_safety_requires_escalation_instruction() -> None:
    template = _valid_template().model_copy(
        update={
            "safety": SafetyPolicy(classification=SafetyClassification.HIGH),
        },
    )

    result = ScenarioManager().validate_template(template)

    assert not result.is_valid
    assert "missing_safety_escalation_instruction" in {
        issue.code for issue in result.errors
    }


def _valid_template() -> ScenarioTemplate:
    return ScenarioTemplate(
        identity=ScenarioIdentity(
            scenario_id="scenario-1",
            slug="schedule-visit",
            display_name="Schedule Visit",
            description="Patient tries to schedule a visit.",
            version=1,
            lifecycle=ScenarioLifecycle.ACTIVE,
            category=ScenarioCategory.SCHEDULING,
        ),
        patient_profile=SyntheticPatientProfile(
            given_name="Jamie",
            family_name="Rivera",
        ),
        objectives=(
            ScenarioObjective(
                objective_id="book-appointment",
                title="Book appointment",
                description="Book a primary care appointment.",
                success_condition="Receptionist offers a suitable appointment time.",
            ),
        ),
        facts=(
            PatientFact(
                key="preferred-day",
                value="Tuesday morning",
                required_for_objective=True,
            ),
        ),
        disclosure_rules=(
            DisclosureRule(
                fact_key="preferred-day",
                timing=DisclosureTiming.WHEN_ASKED,
            ),
        ),
        expected_behaviors=(
            ExpectedReceptionistBehavior(
                expectation_id="ask-reason",
                behavior="Asks for the reason for the visit.",
                reason="The office needs appointment context.",
            ),
        ),
        evaluation_criteria=(
            EvaluationCriterion(
                criterion_id="appointment-offered",
                criterion_type=EvaluationCriterionType.REQUIRED_BEHAVIOR,
                question="Did the receptionist offer an appointment?",
                pass_condition="An appointment option was offered.",
            ),
        ),
        termination_rules=(
            TerminationRule(
                reason=TerminationReason.MAX_DURATION_REACHED,
                condition="End if the call exceeds the allowed duration.",
                max_call_seconds=600,
            ),
        ),
    )
