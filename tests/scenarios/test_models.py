from __future__ import annotations

import pytest
from pydantic import ValidationError

from scenarios import (
    DisclosureRule,
    DisclosureTiming,
    EvaluationCriterion,
    EvaluationCriterionType,
    ExpectedReceptionistBehavior,
    PatientFact,
    ScenarioCategory,
    ScenarioIdentity,
    ScenarioLifecycle,
    ScenarioObjective,
    ScenarioTemplate,
    SyntheticPatientProfile,
    TerminationReason,
    TerminationRule,
)


def test_scenario_template_is_immutable() -> None:
    template = _valid_template()

    with pytest.raises(ValidationError):
        template.identity.display_name = "Changed"


def test_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ScenarioIdentity(
            scenario_id="scenario-1",
            slug="demo-scenario",
            display_name="Demo",
            description="Demo scenario",
            version=1,
            lifecycle=ScenarioLifecycle.ACTIVE,
            category=ScenarioCategory.SCHEDULING,
            unknown_field=True,
        )


def test_slug_fields_are_constrained() -> None:
    with pytest.raises(ValidationError):
        PatientFact(key="Bad Slug", value="Tuesday")


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
