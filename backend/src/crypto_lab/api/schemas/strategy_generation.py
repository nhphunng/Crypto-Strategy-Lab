from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from crypto_lab.api.common import ApiModel
from crypto_lab.domain.market_data.candle import format_utc_millis
from crypto_lab.domain.strategy.generation import (
    GeneratedStrategyDraft,
    GenerationSourceType,
    StrategyGenerationRequest,
    StrategyValidationReport,
)
from crypto_lab.domain.strategy.provenance import StrategySourceSnapshot


class CreateStrategyGenerationRequest(ApiModel):
    source_type: GenerationSourceType = Field(alias="sourceType")
    strategy_name: str | None = Field(
        default=None, min_length=1, max_length=300, alias="strategyName"
    )
    content: str | None = Field(default=None, min_length=1)
    webpage_url: str | None = Field(default=None, alias="webpageUrl")

    @model_validator(mode="after")
    def one_matching_source(self) -> CreateStrategyGenerationRequest:
        values = {
            GenerationSourceType.STRATEGY_NAME: self.strategy_name,
            GenerationSourceType.NATURAL_LANGUAGE: self.content,
            GenerationSourceType.WEBPAGE_URL: self.webpage_url,
        }
        if (
            values[self.source_type] is None
            or sum(item is not None for item in values.values()) != 1
        ):
            raise ValueError("exactly one value matching sourceType is required")
        return self

    @property
    def submitted_value(self) -> str:
        value = self.strategy_name or self.content or self.webpage_url
        assert value is not None
        return value


class DraftSummaryDto(ApiModel):
    id: UUID
    candidate_index: int = Field(alias="candidateIndex")
    normalized_name: str = Field(alias="normalizedName")
    display_name: str = Field(alias="displayName")
    status: str
    draft_fingerprint: str = Field(alias="draftFingerprint")


class GenerationRequestDto(ApiModel):
    id: UUID
    source_type: str = Field(alias="sourceType")
    status: str
    requested_at: str = Field(alias="requestedAt")
    failure: object | None = None
    drafts: tuple[DraftSummaryDto, ...]


class EvidenceDto(ApiModel):
    rule_path: str = Field(alias="rulePath")
    evidence_type: Literal["SOURCE", "ASSUMPTION"] = Field(alias="evidenceType")
    source_locator: str | None = Field(alias="sourceLocator")
    summary: str


class SourceSummaryDto(ApiModel):
    source_type: str = Field(alias="sourceType")
    submitted_url: str | None = Field(alias="submittedUrl")
    canonical_url: str | None = Field(alias="canonicalUrl")
    title: str | None
    attribution: str | None
    content_fingerprint: str = Field(alias="contentFingerprint")
    access_policy_version: str = Field(alias="accessPolicyVersion")
    retrieved_at: str | None = Field(alias="retrievedAt")


class ValidationReportDto(ApiModel):
    id: UUID
    artifact_fingerprint: str = Field(alias="artifactFingerprint")
    policy_version: str = Field(alias="policyVersion")
    status: str
    checks: tuple[dict[str, object], ...]


class GeneratedDraftDto(DraftSummaryDto):
    description: str
    structured_rules: dict[str, object] = Field(alias="structuredRules")
    parameter_definition: tuple[dict[str, object], ...] = Field(alias="parameterDefinition")
    assumptions: tuple[str, ...]
    evidence: tuple[EvidenceDto, ...]
    source_provenance: SourceSummaryDto = Field(alias="sourceProvenance")
    validation_report: ValidationReportDto | None = Field(alias="validationReport")
    failure_issues: tuple[dict[str, object], ...] = Field(alias="failureIssues")


class ActivateGeneratedStrategyRequest(ApiModel):
    draft_fingerprint: str = Field(alias="draftFingerprint")
    artifact_fingerprint: str = Field(alias="artifactFingerprint")
    validation_report_id: UUID = Field(alias="validationReportId")
    confirmed: Literal[True]


def draft_summary(value: GeneratedStrategyDraft) -> DraftSummaryDto:
    return DraftSummaryDto(
        id=value.id,
        candidate_index=value.candidate_index,
        normalized_name=value.normalized_name,
        display_name=value.display_name,
        status=value.status.value,
        draft_fingerprint=value.draft_fingerprint,
    )


def request_dto(
    request: StrategyGenerationRequest, drafts: tuple[GeneratedStrategyDraft, ...]
) -> GenerationRequestDto:
    return GenerationRequestDto(
        id=request.id,
        source_type=request.source_type.value,
        status=request.status.value,
        requested_at=format_utc_millis(request.requested_at),
        drafts=tuple(draft_summary(item) for item in drafts),
    )


def generated_draft_dto(
    draft: GeneratedStrategyDraft,
    source: StrategySourceSnapshot,
    report: StrategyValidationReport | None,
) -> GeneratedDraftDto:
    parameters = tuple(
        {
            "name": item.name,
            "description": item.description,
            "valueType": item.value_type.value,
            "defaultValue": None if item.default_value is None else str(item.default_value),
            "minimum": None if item.minimum is None else str(item.minimum),
            "maximum": None if item.maximum is None else str(item.maximum),
        }
        for item in draft.parameter_schema.definitions
    )
    report_dto = (
        None
        if report is None
        else ValidationReportDto(
            id=report.id,
            artifact_fingerprint=report.artifact_fingerprint,
            policy_version=report.policy_version,
            status=report.status.value,
            checks=tuple(
                {"name": item.name, "status": "PASSED" if item.passed else "FAILED", "findings": []}
                for item in report.checks
            ),
        )
    )
    return GeneratedDraftDto(
        **draft_summary(draft).model_dump(),
        description=draft.description,
        structured_rules=dict(draft.structured_rules),
        parameter_definition=parameters,
        assumptions=draft.assumptions,
        evidence=tuple(
            EvidenceDto(
                rule_path=item.rule_id,
                evidence_type="ASSUMPTION" if item.inferred else "SOURCE",
                source_locator=item.source_location,
                summary=item.source_excerpt,
            )
            for item in draft.evidence
        ),
        source_provenance=SourceSummaryDto(
            source_type=source.source_type.value,
            submitted_url=source.submitted_url,
            canonical_url=source.canonical_url,
            title=source.title,
            attribution=source.attribution,
            content_fingerprint=source.content_fingerprint,
            access_policy_version=source.access_policy_version,
            retrieved_at=format_utc_millis(source.retrieved_at) if source.retrieved_at else None,
        ),
        validation_report=report_dto,
        failure_issues=tuple(
            {"field": item.field, "code": item.code, "message": item.message}
            for item in draft.failure_issues
        ),
    )
