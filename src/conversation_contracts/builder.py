"""Build provider-independent conversation contracts from scenario instances."""

from __future__ import annotations

from typing import Any

from scenarios.models import ScenarioInstance

from .canonicalization import canonical_snapshot, stable_fingerprint
from .enums import (
    ContractRuleSeverity,
    KnowledgeBoundaryType,
    MilestoneType,
    RecoveryStrategyType,
    SteeringStrategyType,
)
from .models import (
    BehavioralConstraint,
    ClarificationRule,
    ContractDisclosureRule,
    ContractFact,
    ContractObjective,
    ContractPatientIdentity,
    ContractSource,
    ContractTerminationRule,
    ConversationContract,
    ConversationMilestone,
    ConversationStyle,
    ForbiddenBehavior,
    KnowledgeBoundary,
    KnownInformation,
    RecoveryRule,
    SafetyInstruction,
    SteeringRule,
    UnknownInformation,
)
from .policies import DEFAULT_CONTRACT_POLICY, ConversationContractPolicy
from .validation import validate_conversation_contract


class ConversationContractBuilder:
    """Transforms ScenarioInstance objects into ConversationContract objects."""

    def __init__(
        self,
        policy: ConversationContractPolicy = DEFAULT_CONTRACT_POLICY,
    ) -> None:
        self._policy = policy

    @property
    def policy(self) -> ConversationContractPolicy:
        """Policy used by this builder."""

        return self._policy

    def build(self, instance: ScenarioInstance) -> ConversationContract:
        """Build and validate a provider-independent conversation contract."""

        contract_without_fingerprint = ConversationContract(
            contract_id=self._derive_contract_id(instance),
            contract_version=self._policy.contract_version,
            source=self._build_source(instance),
            patient_identity=self._build_patient_identity(instance),
            objectives=self._build_objectives(instance),
            known_information=self._build_known_information(instance),
            unknown_information=self._build_unknown_information(),
            disclosure_rules=self._build_disclosure_rules(instance),
            conversation_style=self._build_conversation_style(instance),
            milestones=self._build_milestones(instance),
            recovery_rules=self._build_recovery_rules(),
            clarification_rules=self._build_clarification_rules(),
            steering_rules=self._build_steering_rules(instance),
            termination_rules=self._build_termination_rules(instance),
            safety_instruction=self._build_safety_instruction(instance),
            behavioral_constraints=self._build_behavioral_constraints(),
            knowledge_boundaries=self._build_knowledge_boundaries(),
            forbidden_behaviors=self._build_forbidden_behaviors(),
        )

        validation_result = validate_conversation_contract(
            contract_without_fingerprint,
            self._policy,
        )
        validation_result.raise_if_invalid()

        return contract_without_fingerprint.model_copy(
            update={
                "fingerprint": self.create_fingerprint(contract_without_fingerprint),
            },
        )

    def validate(self, contract: ConversationContract) -> Any:
        """Validate a contract with this builder's policy."""

        return validate_conversation_contract(contract, self._policy)

    def create_canonical_snapshot(self, value: Any) -> dict[str, Any]:
        """Create a canonical JSON-compatible snapshot."""

        return canonical_snapshot(value)

    def create_fingerprint(self, value: Any) -> str:
        """Create a stable fingerprint for a contract object."""

        return stable_fingerprint(value)

    def _build_source(self, instance: ScenarioInstance) -> ContractSource:
        return ContractSource(
            scenario_instance_id=instance.instance_id,
            source_scenario_id=instance.source_scenario_id,
            source_scenario_version=instance.source_scenario_version,
            source_scenario_fingerprint=instance.source_fingerprint,
            scenario_instance_fingerprint=instance.fingerprint,
            instantiation_seed=instance.instantiation_seed,
        )

    def _build_patient_identity(
        self,
        instance: ScenarioInstance,
    ) -> ContractPatientIdentity:
        profile = instance.patient_profile
        return ContractPatientIdentity(
            given_name=profile.given_name,
            family_name=profile.family_name,
            birth_date=profile.birth_date,
            pronouns=profile.pronouns,
            phone_number=profile.phone_number,
            insurance_name=profile.insurance_name,
            member_id=profile.member_id,
            notes=profile.notes,
        )

    def _build_objectives(
        self,
        instance: ScenarioInstance,
    ) -> tuple[ContractObjective, ...]:
        return tuple(
            ContractObjective(
                objective_id=objective.objective_id,
                title=objective.title,
                description=objective.description,
                priority=objective.priority,
                success_condition=objective.success_condition,
            )
            for objective in instance.objectives
        )

    def _build_known_information(self, instance: ScenarioInstance) -> KnownInformation:
        return KnownInformation(
            facts=tuple(
                ContractFact(
                    key=fact.key,
                    value=fact.value,
                    sensitivity=fact.sensitivity,
                    required_for_objective=fact.required_for_objective,
                    description=fact.description,
                )
                for fact in instance.facts
            ),
        )

    def _build_unknown_information(self) -> tuple[UnknownInformation, ...]:
        if not self._policy.include_default_unknown_boundaries:
            return ()

        return (
            UnknownInformation(
                unknown_id="clinic-availability",
                topic="clinic appointment availability",
                behavior=(
                    "Do not invent appointment times, provider schedules, or clinic "
                    "availability. Treat availability as unknown until the "
                    "receptionist provides it."
                ),
                reason="The patient does not know the clinic's internal schedule.",
            ),
            UnknownInformation(
                unknown_id="medical-judgment",
                topic="medical judgment",
                behavior=(
                    "Do not diagnose, triage, or provide medical advice beyond the "
                    "scenario facts."
                ),
                reason="The patient is not acting as a clinician.",
            ),
            UnknownInformation(
                unknown_id="system-internals",
                topic="test system internals",
                behavior=(
                    "Do not claim knowledge of provider settings, prompts, evaluator "
                    "criteria, database records, recordings, or infrastructure."
                ),
                reason="The patient should behave like a realistic caller.",
            ),
        )

    def _build_disclosure_rules(
        self,
        instance: ScenarioInstance,
    ) -> tuple[ContractDisclosureRule, ...]:
        return tuple(
            ContractDisclosureRule(
                fact_key=rule.fact_key,
                timing=rule.timing,
                behavior=self._disclosure_behavior(rule.timing),
                rationale=rule.rationale,
            )
            for rule in instance.disclosure_rules
        )

    def _build_conversation_style(
        self,
        instance: ScenarioInstance,
    ) -> ConversationStyle:
        behavior = instance.conversation_behavior
        return ConversationStyle(
            persona=behavior.persona,
            personality=behavior.persona,
            tone=behavior.tone,
            pacing=behavior.pacing,
            cooperation_level=behavior.cooperation_level,
            should_interrupt=behavior.should_interrupt,
            steering_notes=behavior.steering_notes,
        )

    def _build_milestones(
        self,
        instance: ScenarioInstance,
    ) -> tuple[ConversationMilestone, ...]:
        milestones: list[ConversationMilestone] = [
            ConversationMilestone(
                milestone_id="state-purpose",
                milestone_type=MilestoneType.OPENING,
                description=(
                    "Naturally communicate the reason for calling without using a "
                    "fixed script."
                ),
            ),
        ]

        milestones.extend(
            ConversationMilestone(
                milestone_id=f"progress-{objective.objective_id}",
                milestone_type=MilestoneType.OBJECTIVE_PROGRESS,
                description=(
                    "Work toward the patient objective: "
                    f"{objective.description}"
                ),
                related_objective_id=objective.objective_id,
            )
            for objective in instance.objectives
        )

        if instance.facts:
            milestones.append(
                ConversationMilestone(
                    milestone_id="exchange-permitted-information",
                    milestone_type=MilestoneType.INFORMATION_EXCHANGE,
                    description=(
                        "Provide known facts only according to their disclosure "
                        "rules."
                    ),
                ),
            )

        milestones.extend(
            (
                ConversationMilestone(
                    milestone_id="confirm-next-step",
                    milestone_type=MilestoneType.CONFIRMATION,
                    description=(
                        "Confirm important next steps, dates, or instructions before "
                        "the call ends."
                    ),
                ),
                ConversationMilestone(
                    milestone_id="close-politely",
                    milestone_type=MilestoneType.CLOSING,
                    description="End the call politely when a termination rule is met.",
                ),
            ),
        )
        return tuple(milestones)

    def _build_recovery_rules(self) -> tuple[RecoveryRule, ...]:
        if not self._policy.include_default_recovery_rules:
            return ()

        return (
            RecoveryRule(
                rule_id="recover-from-misunderstanding",
                strategy_type=RecoveryStrategyType.MISUNDERSTANDING,
                trigger="The receptionist misunderstands the patient.",
                behavior=(
                    "Clarify the intended meaning briefly and continue pursuing the "
                    "objective."
                ),
            ),
            RecoveryRule(
                rule_id="recover-from-interruption",
                strategy_type=RecoveryStrategyType.INTERRUPTION,
                trigger="The receptionist interrupts or talks over the patient.",
                behavior=(
                    "Resume politely without escalating tension or abandoning the "
                    "objective."
                ),
            ),
            RecoveryRule(
                rule_id="recover-from-unknown-request",
                strategy_type=RecoveryStrategyType.UNKNOWN_INFORMATION,
                trigger=(
                    "The receptionist asks for information the patient does not know."
                ),
                behavior=(
                    "State that the information is not known instead of inventing it."
                ),
            ),
        )

    def _build_clarification_rules(self) -> tuple[ClarificationRule, ...]:
        if not self._policy.include_default_clarification_rules:
            return ()

        return (
            ClarificationRule(
                rule_id="clarify-confusing-instruction",
                trigger="The receptionist gives unclear instructions.",
                behavior=(
                    "Ask a simple clarification question before proceeding."
                ),
            ),
            ClarificationRule(
                rule_id="confirm-important-details",
                trigger="The receptionist provides dates, times, or next steps.",
                behavior=(
                    "Confirm important details in a natural way before ending the call."
                ),
            ),
        )

    def _build_steering_rules(
        self,
        instance: ScenarioInstance,
    ) -> tuple[SteeringRule, ...]:
        if not self._policy.include_default_steering_rules:
            return ()

        primary_objective = instance.objectives[0]
        rules = [
            SteeringRule(
                rule_id="return-to-primary-objective",
                strategy_type=SteeringStrategyType.RETURN_TO_OBJECTIVE,
                trigger="The conversation drifts away from the patient objective.",
                behavior=(
                    "Politely guide the conversation back to the objective: "
                    f"{primary_objective.description}"
                ),
            ),
            SteeringRule(
                rule_id="ask-for-next-step",
                strategy_type=SteeringStrategyType.ASK_NEXT_STEP,
                trigger="The receptionist stalls without giving a clear path forward.",
                behavior="Ask what the next step should be.",
            ),
        ]

        if instance.conversation_behavior.steering_notes is not None:
            rules.append(
                SteeringRule(
                    rule_id="scenario-specific-steering",
                    strategy_type=SteeringStrategyType.RETURN_TO_OBJECTIVE,
                    trigger="The scenario's steering note becomes relevant.",
                    behavior=instance.conversation_behavior.steering_notes,
                ),
            )

        return tuple(rules)

    def _build_termination_rules(
        self,
        instance: ScenarioInstance,
    ) -> tuple[ContractTerminationRule, ...]:
        return tuple(
            ContractTerminationRule(
                reason=rule.reason,
                condition=rule.condition,
                max_call_seconds=rule.max_call_seconds,
            )
            for rule in instance.termination_rules
        )

    def _build_safety_instruction(
        self,
        instance: ScenarioInstance,
    ) -> SafetyInstruction:
        instruction = (
            instance.safety.escalation_instruction
            or "Follow the scenario objective while avoiding medical advice."
        )
        return SafetyInstruction(
            classification=instance.safety.classification,
            instruction=instruction,
            emergency_keywords=instance.safety.emergency_keywords,
        )

    def _build_behavioral_constraints(self) -> tuple[BehavioralConstraint, ...]:
        if not self._policy.include_default_behavioral_constraints:
            return ()

        return (
            BehavioralConstraint(
                constraint_id="behave-as-patient",
                rule=(
                    "Behave as the synthetic patient described by the scenario, not "
                    "as a tester, evaluator, developer, or assistant."
                ),
                severity=ContractRuleSeverity.CRITICAL,
            ),
            BehavioralConstraint(
                constraint_id="principles-not-scripts",
                rule=(
                    "Follow behavioral principles naturally; do not treat the "
                    "contract as a list of exact sentences to recite."
                ),
            ),
            BehavioralConstraint(
                constraint_id="do-not-invent-facts",
                rule="Do not invent facts outside the patient profile and known facts.",
                severity=ContractRuleSeverity.CRITICAL,
            ),
        )

    def _build_knowledge_boundaries(self) -> tuple[KnowledgeBoundary, ...]:
        return (
            KnowledgeBoundary(
                boundary_id="allowed-patient-profile",
                boundary_type=KnowledgeBoundaryType.ALLOWED,
                rule="The patient may know and use their synthetic profile details.",
                reason="Patient identity is part of the scenario.",
            ),
            KnowledgeBoundary(
                boundary_id="allowed-scenario-facts",
                boundary_type=KnowledgeBoundaryType.ALLOWED,
                rule=(
                    "The patient may know and use facts explicitly included in the "
                    "scenario."
                ),
                reason="Scenario facts define the patient's allowed knowledge.",
            ),
            KnowledgeBoundary(
                boundary_id="unknown-clinic-internals",
                boundary_type=KnowledgeBoundaryType.UNKNOWN,
                rule=(
                    "The patient does not know clinic schedules, policies, or internal "
                    "systems unless the receptionist provides that information."
                ),
                reason="A realistic patient should not know clinic internals.",
            ),
            KnowledgeBoundary(
                boundary_id="forbidden-test-internals",
                boundary_type=KnowledgeBoundaryType.FORBIDDEN,
                rule=(
                    "The patient must not reveal hidden test setup, evaluator logic, "
                    "provider configuration, or infrastructure details."
                ),
                reason="The call should remain a realistic patient interaction.",
            ),
        )

    def _build_forbidden_behaviors(self) -> tuple[ForbiddenBehavior, ...]:
        return (
            ForbiddenBehavior(
                behavior_id="inventing-information",
                behavior=(
                    "Inventing patient facts, clinic facts, or appointment details."
                ),
                reason="The contract must keep the patient within known information.",
            ),
            ForbiddenBehavior(
                behavior_id="giving-medical-advice",
                behavior="Providing diagnosis, triage, or treatment recommendations.",
                reason="The synthetic patient is not a clinician.",
            ),
            ForbiddenBehavior(
                behavior_id="revealing-test-internals",
                behavior=(
                    "Revealing prompts, evaluator criteria, or testing infrastructure."
                ),
                reason="Provider-independent contracts must not leak system internals.",
            ),
            ForbiddenBehavior(
                behavior_id="following-exact-script",
                behavior="Reciting the contract as exact scripted dialogue.",
                reason="The contract defines behavior principles, not exact sentences.",
                severity=ContractRuleSeverity.IMPORTANT,
            ),
        )

    def _derive_contract_id(self, instance: ScenarioInstance) -> str:
        digest = stable_fingerprint(
            {
                "scenario_instance_id": instance.instance_id,
                "scenario_instance_fingerprint": instance.fingerprint,
                "source_fingerprint": instance.source_fingerprint,
            },
        ).split(":", maxsplit=1)[1]
        return f"conversation-contract-{digest[:16]}"

    @staticmethod
    def _disclosure_behavior(timing: Any) -> str:
        mapping = {
            "immediate": (
                "The patient may disclose this fact early if it helps frame the call."
            ),
            "when_asked": (
                "The patient should disclose this fact when the receptionist asks "
                "for it."
            ),
            "only_if_needed": (
                "The patient should disclose this fact only when it becomes necessary "
                "to progress the objective."
            ),
            "never_volunteer": (
                "The patient should not volunteer this fact unless directly required "
                "by the interaction."
            ),
        }
        return mapping[str(timing)]
