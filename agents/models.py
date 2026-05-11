"""Data models for agent inputs, outputs, and shared structures."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ── Enums ────────────────────────────────────────────────────────────────────

class InspectionMode(str, Enum):
    inspection = "inspection"
    align = "align"


class AlgorithmCategory(str, Enum):
    BLOB = "BLOB"
    COLOR_FILTER = "COLOR_FILTER"
    EDGE_DETECTION = "EDGE_DETECTION"
    TEMPLATE_MATCHING = "TEMPLATE_MATCHING"


class FailureReason(str, Enum):
    pipeline_bad_fit = "pipeline_bad_fit"
    pipeline_bad_params = "pipeline_bad_params"
    algorithm_wrong_category = "algorithm_wrong_category"
    algorithm_runtime_error = "algorithm_runtime_error"
    inspection_plan_issue = "inspection_plan_issue"
    spec_issue = "spec_issue"


class DecisionType(str, Enum):
    rule_based = "rule_based"
    edge_learning = "edge_learning"
    deep_learning = "deep_learning"
    hw_improvement = "hw_improvement"


class DefectScale(str, Enum):
    macro = "macro"
    micro = "micro"
    texture = "texture"


class IlluminationType(str, Enum):
    uniform = "uniform"
    gradient = "gradient"
    spot = "spot"
    uneven = "uneven"


class NoiseFrequency(str, Enum):
    high_freq = "high_freq"
    low_freq = "low_freq"


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class ImageDiagnosis:
    contrast: float
    noise_level: float
    edge_density: float
    lighting_uniformity: float
    illumination_type: IlluminationType
    noise_frequency: NoiseFrequency
    reflection_level: float
    texture_complexity: float
    surface_type: str
    defect_scale: DefectScale
    blob_feasibility: float
    blob_count_estimate: int
    blob_size_variance: float
    color_discriminability: float
    dominant_channel_ratio: float
    structural_regularity: float
    pattern_repetition: float
    background_uniformity: float
    optimal_color_space: str
    threshold_candidate: float
    edge_sharpness: float


@dataclass
class PipelineBlock:
    name: str
    when_condition: str
    params: Optional[dict] = None


@dataclass
class ProcessingPipeline:
    name: str
    blocks: list[PipelineBlock] = field(default_factory=list)
    score: float = 0.0


@dataclass
class JudgementResult:
    visibility_score: float
    separability_score: float
    measurability_score: float
    problems: list[str] = field(default_factory=list)
    next_suggestion: str = ""


@dataclass
class InspectionItem:
    id: int
    name: str
    purpose: str
    method: AlgorithmCategory
    depends_on: list[int] = field(default_factory=list)
    safety_role: str = ""
    success_criteria: str = ""


@dataclass
class InspectionPlan:
    items: list[InspectionItem] = field(default_factory=list)
    mode: InspectionMode = InspectionMode.inspection


@dataclass
class SpecResult:
    mode: InspectionMode
    goal: str
    success_criteria: dict = field(default_factory=dict)


@dataclass
class TestMetrics:
    accuracy: Optional[float] = None
    fp_rate: Optional[float] = None
    fn_rate: Optional[float] = None
    coord_error: Optional[float] = None
    success_rate: Optional[float] = None


@dataclass
class ItemTestResult:
    item_id: int
    item_name: str
    passed: bool
    metrics: TestMetrics = field(default_factory=TestMetrics)
    details: str = ""


@dataclass
class EvaluationResult:
    overall_passed: bool
    failure_reason: Optional[FailureReason]
    failed_items: list[int] = field(default_factory=list)
    analysis: str = ""


@dataclass
class FeedbackAction:
    target_agent: str
    reason: FailureReason
    context: dict = field(default_factory=dict)
    retry_count: int = 0


@dataclass
class DecisionResult:
    decision: DecisionType
    reason: str
    confidence: float
    details: dict = field(default_factory=dict)


@dataclass
class AgentDirectives:
    orchestrator: Optional[str] = None
    spec: Optional[str] = None
    image_analysis: Optional[str] = None
    pipeline_composer: Optional[str] = None
    vision_judge: Optional[str] = None
    inspection_plan: Optional[str] = None
    algorithm_coder: Optional[str] = None
    test: Optional[str] = None


@dataclass
class ExecutionProgress:
    current_agent: str
    current_iteration: int
    status: str
    message: str


@dataclass
class AlgorithmResult:
    code: str
    explanation: str
    category: AlgorithmCategory
    pipeline: ProcessingPipeline
