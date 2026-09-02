"""API reutilizavel do pipeline Python RLINE/AERMOD."""

from .analysis import (
    DEFAULT_COORDINATE_TOLERANCE,
    aggregate_rline_period,
    calculate_metrics,
    load_case_results,
    merge_one_to_one,
    road_segment_mask,
)
from .config import (
    SCHEMA_VERSION,
    CaseConfig,
    GridConfig,
    decimal_grid_axes,
    generate_grid,
    load_case_config,
    validate_case_config,
)
from .errors import ConfigValidationError, PipelineValidationError
from .generation import generate_case
from .parsing import (
    parse_aermod,
    parse_rline,
    validate_aermod_completion,
    validate_rline_output,
)
from .plotting import concentration_pivot, plot_cases_summary, process_case

__all__ = [
    "DEFAULT_COORDINATE_TOLERANCE",
    "SCHEMA_VERSION",
    "CaseConfig",
    "ConfigValidationError",
    "GridConfig",
    "PipelineValidationError",
    "aggregate_rline_period",
    "calculate_metrics",
    "decimal_grid_axes",
    "generate_grid",
    "generate_case",
    "load_case_config",
    "load_case_results",
    "merge_one_to_one",
    "parse_aermod",
    "parse_rline",
    "plot_cases_summary",
    "process_case",
    "concentration_pivot",
    "road_segment_mask",
    "validate_aermod_completion",
    "validate_rline_output",
    "validate_case_config",
]
