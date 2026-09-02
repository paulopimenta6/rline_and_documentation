"""Excecoes publicas do pipeline."""


class PipelineValidationError(ValueError):
    """Indica entrada ou resultado inconsistente/incompleto."""


class ConfigValidationError(PipelineValidationError):
    """Indica configuracao de caso invalida."""
