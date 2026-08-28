from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from uuid import UUID

from crypto_lab.domain.strategy.errors import ErrorIssue
from crypto_lab.domain.strategy.parameters import ParameterSchema
from crypto_lab.domain.strategy.version import SemanticVersion


class GenerationSourceType(StrEnum):
    STRATEGY_NAME = "STRATEGY_NAME"
    NATURAL_LANGUAGE = "NATURAL_LANGUAGE"
    WEBPAGE_URL = "WEBPAGE_URL"


class GenerationRequestStatus(StrEnum):
    RECEIVED = "RECEIVED"
    SOURCE_PREPARING = "SOURCE_PREPARING"
    GENERATING = "GENERATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DraftStatus(StrEnum):
    NEEDS_REVIEW = "NEEDS_REVIEW"
    VALIDATING = "VALIDATING"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    READY_FOR_CONFIRMATION = "READY_FOR_CONFIRMATION"
    REJECTED = "REJECTED"
    ACTIVATED = "ACTIVATED"
    ARCHIVED = "ARCHIVED"


class ValidationStatus(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True, slots=True)
class StrategyGenerationRequest:
    id: UUID
    source_type: GenerationSourceType
    submitted_value: str
    status: GenerationRequestStatus
    requested_at: datetime
    updated_at: datetime
    source_snapshot_id: UUID | None = None
    failure_category: str | None = None
    failure_message: str | None = None

    def __post_init__(self) -> None:
        if not self.submitted_value.strip():
            raise ValueError("generation input must not be blank")


@dataclass(frozen=True, slots=True)
class RuleEvidence:
    rule_id: str
    source_excerpt: str
    source_location: str | None
    inferred: bool = False


@dataclass(frozen=True, slots=True)
class GeneratedStrategyDraft:
    id: UUID
    generation_request_id: UUID
    source_snapshot_id: UUID
    candidate_index: int
    normalized_name: str
    display_name: str
    description: str
    structured_rules: Mapping[str, object]
    parameter_schema: ParameterSchema
    assumptions: tuple[str, ...]
    evidence: tuple[RuleEvidence, ...]
    status: DraftStatus = DraftStatus.NEEDS_REVIEW
    generated_artifact_id: UUID | None = None
    validation_report_id: UUID | None = None
    failure_issues: tuple[ErrorIssue, ...] = ()

    def __post_init__(self) -> None:
        if self.candidate_index < 0 or not self.normalized_name or not self.display_name:
            raise ValueError("draft identity is invalid")
        object.__setattr__(self, "structured_rules", MappingProxyType(dict(self.structured_rules)))

    @property
    def draft_fingerprint(self) -> str:
        payload = {
            "assumptions": self.assumptions,
            "candidateIndex": self.candidate_index,
            "name": self.normalized_name,
            "parameterSchema": self.parameter_schema.fingerprint,
            "rules": dict(self.structured_rules),
        }
        return hashlib.sha256(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class GeneratedStrategyArtifact:
    id: UUID
    draft_id: UUID
    source_code: str
    content_fingerprint: str
    contract_version: SemanticVersion
    declared_imports: frozenset[str]
    capabilities: frozenset[str]
    created_at: datetime
    language: str = "python"
    language_version: str = "3.12"

    @classmethod
    def create(
        cls,
        *,
        id: UUID,
        draft_id: UUID,
        source_code: str,
        contract_version: SemanticVersion,
        declared_imports: frozenset[str],
        capabilities: frozenset[str],
        created_at: datetime,
    ) -> GeneratedStrategyArtifact:
        normalized = source_code.replace("\r\n", "\n").rstrip() + "\n"
        return cls(
            id,
            draft_id,
            normalized,
            hashlib.sha256(normalized.encode()).hexdigest(),
            contract_version,
            declared_imports,
            capabilities,
            created_at,
        )


@dataclass(frozen=True, slots=True)
class ValidationCheck:
    name: str
    passed: bool
    message: str


@dataclass(frozen=True, slots=True)
class StrategyValidationReport:
    id: UUID
    artifact_id: UUID
    artifact_fingerprint: str
    policy_version: str
    status: ValidationStatus
    checks: tuple[ValidationCheck, ...]
    findings: tuple[ErrorIssue, ...]
    started_at: datetime
    completed_at: datetime
    environment_fingerprint: str

    @property
    def passed(self) -> bool:
        return self.status is ValidationStatus.PASSED and all(item.passed for item in self.checks)
