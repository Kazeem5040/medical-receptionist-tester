from __future__ import annotations

import pytest

from scenarios import (
    ControlledVariation,
    DisclosureRule,
    DisclosureTiming,
    EvaluationCriterion,
    EvaluationCriterionType,
    ExpectedReceptionistBehavior,
    PatientFact,
    ScenarioCategory,
    ScenarioIdentity,
    ScenarioLifecycle,
    ScenarioManager,
    ScenarioObjective,
    ScenarioTemplate,
    ScenarioValidationError,
    SyntheticPatientProfile,
    TerminationReason,
    TerminationRule,
    VariationOption,
)


def test_instance_creation_is_deterministic_for_same_seed() -> None:
    manager = ScenarioManager()
    template = _valid_template_with_variation()

    first = manager.create_instance(template, seed="seed-1")
    second = manager.create_instance(template, seed="seed-1")

    assert first == second
    assert first.fingerprint == second.fingerprint
    assert first.selected_variations == second.selected_variations


def test_different_seeds_keep_source_fingerprint_stable() -> None:
    manager = ScenarioManager()
    template = _valid_template_with_variation()

    first = manager.create_instance(template, seed="seed-1")
    second = manager.create_instance(template, seed="seed-2")

    assert first.source_fingerprint == second.source_fingerprint
    assert first.instantiation_seed != second.instantiation_seed


def test_inactive_template_cannot_be_instantiated() -> None:
    template = _valid_template_with_variation()
    inactive = template.model_copy(
        update={
            "identity": template.identity.model_copy(
                update={"lifecycle": ScenarioLifecycle.DRAFT},
            ),
        },
    )

    with pytest.raises(ScenarioValidationError):
        ScenarioManager().create_instance(inactive, seed="seed-1")


def _valid_template_with_variation() -> ScenarioTemplate:
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
        variations=(
            ControlledVariation(
                variation_id="patient-mood",
                name="Patient mood",
                options=(
                    VariationOption(option_id="calm", value="calm"),
                    VariationOption(option_id="rushed", value="rushed"),
                ),
            ),
        ),
    )
