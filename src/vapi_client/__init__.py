"""Vapi HTTP API Client package."""

from .client import VapiApiClient
from .enums import (
    HttpMethod,
    ProviderResourceStatus,
    RetryReason,
    VapiClientValidationSeverity,
    VapiResponseStatus,
)
from .errors import (
    VapiAuthenticationError,
    VapiClientError,
    VapiNetworkError,
    VapiRateLimitError,
    VapiResponseValidationError,
    VapiSerializationError,
    VapiServerError,
    VapiTimeoutError,
)
from .models import (
    VapiAssistantId,
    VapiCallId,
    VapiCreateAssistantRequest,
    VapiCreateAssistantResponse,
    VapiHttpStatus,
    VapiProviderMetadata,
)
from .policies import DEFAULT_VAPI_CLIENT_POLICY, VapiClientPolicy

__all__ = [
    "DEFAULT_VAPI_CLIENT_POLICY",
    "HttpMethod",
    "ProviderResourceStatus",
    "RetryReason",
    "VapiApiClient",
    "VapiAssistantId",
    "VapiAuthenticationError",
    "VapiCallId",
    "VapiClientError",
    "VapiClientPolicy",
    "VapiClientValidationSeverity",
    "VapiCreateAssistantRequest",
    "VapiCreateAssistantResponse",
    "VapiHttpStatus",
    "VapiNetworkError",
    "VapiProviderMetadata",
    "VapiRateLimitError",
    "VapiResponseStatus",
    "VapiResponseValidationError",
    "VapiSerializationError",
    "VapiServerError",
    "VapiTimeoutError",
]
