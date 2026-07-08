"""Public service for validating and instantiating scenarios."""

from __future__ import annotations

import hashlib
from typing import Any

from .canonicalization import canonical_snapshot, stable_fingerprint
from .enums import ScenarioLifecycle
from .errors import ScenarioValidationIssue, ScenarioValidationResult
from .models import ResolvedVariation, ScenarioInstance, ScenarioTemplate
from .policies import DEFAULT_VALIDATION_POLICY, ScenarioValidationPolicy
from .validation import validate_scenario_template


class ScenarioManager:
    """Stateless domain service for scenario operations."""

    def __init__(
        self,
        policy: ScenarioValidationPolicy = DEFAULT_VALIDATION_POLICY,
    ) -> None:
        self._policy = policy

    @property
    def policy(self) -> ScenarioValidationPolicy:
        """Validation policy used by this manager."""

        return self._policy

    def validate_template(
        self,
        template: ScenarioTemplate,
    ) -> ScenarioValidationResult:
        """Validate a scenario template and return structured issues."""

        return validate_scenario_template(template, self._policy)

    def create_instance(
        self,
        template: ScenarioTemplate,
        *,
        seed: str | int | None = None,
        instance_id: str | None = None,
    ) -> ScenarioInstance:
        """Create a deterministic scenario instance from a template."""

        validation_result = self.validate_template(template)
        issues = list(validation_result.issues)

        if (
            self._policy.require_active_lifecycle_for_instantiation
            and template.identity.lifecycle != ScenarioLifecycle.ACTIVE
        ):
            issues.append(
                ScenarioValidationIssue(
                    code="scenario_not_active",
                    message="Only active scenarios can be instantiated.",
                    path=("identity", "lifecycle"),
                ),
            )

        result = ScenarioValidationResult.from_issues(issues)
        result.raise_if_invalid()

        source_fingerprint = self.create_fingerprint(template)
        instantiation_seed = str(
            seed
            if seed is not None
            else f"{template.identity.scenario_id}:{template.identity.version}",
        )
        selected_variations = self._resolve_variations(
            template=template,
            source_fingerprint=source_fingerprint,
            seed=instantiation_seed,
        )

        resolved_instance_id = instance_id or self._derive_instance_id(
            source_fingerprint=source_fingerprint,
            seed=instantiation_seed,
            selected_variations=selected_variations,
        )

        instance_without_fingerprint = ScenarioInstance(
            instance_id=resolved_instance_id,
            source_scenario_id=template.identity.scenario_id,
            source_scenario_version=template.identity.version,
            source_fingerprint=source_fingerprint,
            instantiation_seed=instantiation_seed,
            identity=template.identity,
            patient_profile=template.patient_profile,
            objectives=template.objectives,
            facts=template.facts,
            disclosure_rules=template.disclosure_rules,
            conversation_behavior=template.conversation_behavior,
            expected_behaviors=template.expected_behaviors,
            prohibited_behaviors=template.prohibited_behaviors,
            evaluation_criteria=template.evaluation_criteria,
            safety=template.safety,
            termination_rules=template.termination_rules,
            selected_variations=selected_variations,
        )
        fingerprint = self.create_fingerprint(instance_without_fingerprint)
        return instance_without_fingerprint.model_copy(
            update={"fingerprint": fingerprint},
        )

    def create_canonical_snapshot(self, value: Any) -> dict[str, Any]:
        """Create a canonical JSON-compatible snapshot."""

        return canonical_snapshot(value)

    def create_fingerprint(self, value: Any) -> str:
        """Create a stable fingerprint for a scenario object."""

        return stable_fingerprint(value)

    def _resolve_variations(
        self,
        *,
        template: ScenarioTemplate,
        source_fingerprint: str,
        seed: str,
    ) -> tuple[ResolvedVariation, ...]:
        selected: list[ResolvedVariation] = []

        for variation in template.variations:
            option_index = self._deterministic_index(
                parts=(source_fingerprint, seed, variation.variation_id),
                modulo=len(variation.options),
            )
            option = variation.options[option_index]
            selected.append(
                ResolvedVariation(
                    variation_id=variation.variation_id,
                    option_id=option.option_id,
                    value=option.value,
                ),
            )

        return tuple(selected)

    def _derive_instance_id(
        self,
        *,
        source_fingerprint: str,
        seed: str,
        selected_variations: tuple[ResolvedVariation, ...],
    ) -> str:
        payload = {
            "source_fingerprint": source_fingerprint,
            "seed": seed,
            "selected_variations": selected_variations,
        }
        digest = stable_fingerprint(payload).split(":", maxsplit=1)[1]
        return f"scenario-instance-{digest[:16]}"

    @staticmethod
    def _deterministic_index(*, parts: tuple[str, ...], modulo: int) -> int:
        joined = "\u241f".join(parts)
        digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()
        return int(digest, 16) % modulo
