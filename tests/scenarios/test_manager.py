from __future__ import annotations

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
    ScenarioManager,
    ScenarioObjective,
    ScenarioTemplate,
    SyntheticPatientProfile,
    TerminationReason,
    TerminationRule,
)


def test_manager_exposes_validation_snapshot_and_fingerprint() -> None:
    manager = ScenarioManager()
    template = _valid_template()

    result = manager.validate_template(template)
    snapshot = manager.create_canonical_snapshot(template)
    fingerprint = manager.create_fingerprint(template)

    assert result.is_valid
    assert snapshot["identity"]["scenario_id"] == "scenario-1"
    assert fingerprint.startswith("sha256:")


def test_instance_contains_evaluation_contract_fields() -> None:
    instance = ScenarioManager().create_instance(_valid_template(), seed="seed-1")

    contract = instance.evaluation_contract()

    assert contract["objectives"] == instance.objectives
    assert contract["expected_behaviors"] == instance.expected_behaviors
    assert contract["prohibited_behaviors"] == instance.prohibited_behaviors
    assert contract["evaluation_criteria"] == instance.evaluation_criteria
    assert contract["safety"] == instance.safety


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
