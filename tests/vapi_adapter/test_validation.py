from __future__ import annotations

from tests.vapi_adapter_factories import conversation_contract
from vapi_adapter import VapiProviderAdapter
from vapi_adapter.validation import validate_vapi_configuration


def test_valid_configuration_has_no_validation_errors() -> None:
    configuration = VapiProviderAdapter().build(conversation_contract())

    result = validate_vapi_configuration(configuration)

    assert result.is_valid
    assert result.errors == ()


def test_missing_critical_mapping_coverage_is_error() -> None:
    configuration = VapiProviderAdapter().build(conversation_contract())
    invalid = configuration.model_copy(
        update={
            "mapping_coverage": tuple(
                item
                for item in configuration.mapping_coverage
                if item.contract_section != "objectives"
            ),
        },
    )

    result = validate_vapi_configuration(invalid)

    assert not result.is_valid
    assert "missing_mapping_coverage" in {issue.code for issue in result.errors}


def test_missing_contract_fingerprint_is_error() -> None:
    configuration = VapiProviderAdapter().build(conversation_contract())
    invalid = configuration.model_copy(
        update={
            "source_traceability": configuration.source_traceability.model_copy(
                update={"conversation_contract_fingerprint": None},
            ),
        },
    )

    result = validate_vapi_configuration(invalid)

    assert not result.is_valid
    assert "missing_contract_fingerprint" in {
        issue.code for issue in result.errors
    }
