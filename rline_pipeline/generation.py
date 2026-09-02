"""Geracao deterministica dos arquivos de entrada de um caso."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
import tempfile

from ._io import publish_file_set
from .config import CaseConfig, decimal_grid_axes, load_case_config
from .errors import PipelineValidationError


def _decimal(value: float) -> Decimal:
    return Decimal(str(value))


def _format_decimal(value: float | Decimal) -> str:
    decimal_value = value if isinstance(value, Decimal) else _decimal(value)
    return format(decimal_value, "f")


def _rline_emission(config: CaseConfig) -> Decimal:
    if config.emis_fator is not None:
        return _decimal(config.emis_fator)
    return _decimal(config.qs) * _decimal(config.width)


def build_aermod_control(config: CaseConfig, *, title: str | None = None) -> str:
    """Monta o control file AERMOD de forma deterministica."""

    grid = config.grid
    titleone = config.nome.upper() if title is None else title
    return "".join(
        [
            "CO STARTING\n",
            f"   TITLEONE   {titleone}\n",
            "   MODELOPT   DFAULT CONC\n",
            "   AVERTIME   PERIOD\n",
            "   POLLUTID   OTHER\n",
            "   RUNORNOT   RUN\n",
            "CO FINISHED\n\n",
            "SO STARTING\n",
            "   LOCATION   HWY1    RLINE  0.0  "
            f"{_format_decimal(config.y_rodovia)}  "
            f"{_format_decimal(config.comprimento)}  "
            f"{_format_decimal(config.y_rodovia)}\n",
            "   SRCPARAM   HWY1   "
            f"{_format_decimal(config.qs)}  0.0   {_format_decimal(config.width)}\n",
            "   SRCGROUP   ALL\n",
            "SO FINISHED\n\n",
            "RE STARTING\n",
            "   GRIDCART   RCART STA\n",
            "   GRIDCART   RCART XYINC  "
            f"{_format_decimal(grid.xini)}  {grid.xn}  "
            f"{_format_decimal(grid.xdelta)}  {_format_decimal(grid.yini)}  "
            f"{grid.yn}  {_format_decimal(grid.ydelta)}\n",
            "   GRIDCART   RCART END\n",
            "RE FINISHED\n\n",
            "ME STARTING\n",
            "   SURFFILE   ONSITE.SFC\n",
            "   PROFFILE   ONSITE.PFL\n",
            "   SURFDATA   99999  1988\n",
            "   UAIRDATA   99999  1988\n",
            "   SITEDATA   99999  1988\n",
            "   PROFBASE   10.0 METERS\n",
            "ME FINISHED\n\n",
            "OU STARTING\n",
            "   RECTABLE   ALLAVE FIRST\n",
            "   PLOTFILE   PERIOD ALL CONC_PLOT.PLT\n",
            "   MAXTABLE   ALLAVE 20\n",
            "OU FINISHED\n",
        ]
    )


def build_receptor_file(config: CaseConfig) -> str:
    """Monta receptores sem truncar ou arredondar as coordenadas da grade."""

    xs, ys = decimal_grid_axes(config.grid)
    lines = [
        "This file contains receptor locations\n",
        "X_coordinate  Y_Coordinate  Z_Coordinate\n",
        "----------------------------------------------\n",
    ]
    lines.extend(f"  {_format_decimal(x)} {_format_decimal(y)} 0.0\n" for y in ys for x in xs)
    return "".join(lines)


def build_source_file(config: CaseConfig) -> str:
    """Monta a fonte linear com a geometria e emissao efetivas do caso."""

    return "".join(
        [
            "Source input file\n",
            "Group  X_b    Y_b    Z_b    X_e    Y_e    Z_e  dCL  sigmaz0 "
            "#lanes  Emis  Hw1  dw1  Hw2  dw2 Depth  Wtop  Wbottom\n",
            "----------------------------------------------\n",
            "HWY 0.0 "
            f"{_format_decimal(config.y_rodovia)} 0.0 "
            f"{_format_decimal(config.comprimento)} "
            f"{_format_decimal(config.y_rodovia)} 0.0 0.0 0.0 1.0 "
            f"{_format_decimal(_rline_emission(config))} "
            "0.0 0.0 0.0 0.0 0.0 0.0 0.0\n",
        ]
    )


def build_line_source_inputs(config: CaseConfig, *, meteorology_path: str = "./ONSITE.SFC") -> str:
    """Monta o arquivo de controle posicional do RLINE."""

    return "".join(
        [
            "User control file for RLINEv1_2\n",
            "Source File Name\n",
            "'Source_Road.txt'\n",
            "Input Emiss can be in AADT or g/m (see user guide)\n",
            "--------------------------------------------------\n",
            "Receptor File Name\n",
            "'Receptor_Road.txt'\n",
            "--------------------------------------------------\n",
            "Input Met File\n",
            f"'{meteorology_path}'\n",
            "--------------------------------------------------\n",
            "Receptor Output File\n",
            "'Output_Road_Numerical.csv'\n",
            "--------------------------------------------------\n",
            "Error_Limit (suggested 1.0e-03)\n",
            "1.0e-03\n",
            "--------------------------------------------------\n",
            "Ratio of displacement height to roughness length (fac_dispht)\n",
            "5.0\n",
            "--------------------------------------------------\n",
            "--- OUTPUT OPTION(S) BELOW: ----------------------\n",
            "--------------------------------------------------\n",
            "(1) Include concentrations from ['M'] Meander ONLY, "
            "['P'] Plume ONLY, ['T'] Total = Plume+Meander\n",
            "'T'\n",
            "--------------------------------------------------\n",
            "(2) Outout daily 24-hour averages? ('Y'/'N')\n",
            "'Y'\n",
            "--------------------------------------------------\n",
            "(3) ['M'] Monthly Output Files, ['N'] No Hourly Files, ['A'] All hourly in one file\n",
            "'A'\n",
            "--------------------------------------------------\n",
            "(4) Supress source/receptor proximity warnings? ('Y'/'N')\n",
            "'Y'\n",
            "--------------------------------------------------\n",
            "--- BETA OPTION(S) BELOW: ------------------------\n",
            "--------------------------------------------------\n",
            "(1) Use analytical solution ('Y'/'N'), speeds up run time, but less accurate\n",
            "'N'\n",
            "--------------------------------------------------\n",
            "(2) Use barrier and depressed roadway algorithms? ('Y'/'N')\n",
            "'N'\n",
            "--------------------------------------------------\n",
            "(3) Use non-zero roadwidth? ('Y'/'N')Lane width [m]\n",
            f"'Y' {_format_decimal(config.width)}\n",
            "--------------------------------------------------\n",
        ]
    )


def build_metadata(config: CaseConfig) -> str:
    """Monta os metadados textuais sem informacoes variaveis de execucao."""

    return "".join(
        [
            f"nome        : {config.nome}\n",
            f"descricao   : {config.descricao}\n",
            f"comprimento : {_format_decimal(config.comprimento)} m\n",
            f"y_rodovia   : {_format_decimal(config.y_rodovia)} m\n",
            f"qs (Lnemis) : {_format_decimal(config.qs)} g/s/m2\n",
            f"width       : {_format_decimal(config.width)} m\n",
            f"emis RLINE  : {_format_decimal(_rline_emission(config))} g/m/s\n",
            f"receptores  : {config.numero_receptores} (grid {config.grid.xn}x{config.grid.yn})\n",
            f"transecto_x : {_format_decimal(config.transecto_x)} m\n",
            f"periodos    : {config.periodos_esperados}\n",
        ]
    )


def generated_case_files(
    config: CaseConfig,
    *,
    aermod_title: str | None = None,
    rline_meteorology_path: str = "./ONSITE.SFC",
) -> dict[Path, str]:
    """Return every deterministic case input relative to the case directory."""

    return {
        Path("controles_aermod/RLINE_TEST.INP"): build_aermod_control(config, title=aermod_title),
        Path("rodada_rline/Receptor_Road.txt"): build_receptor_file(config),
        Path("rodada_rline/Source_Road.txt"): build_source_file(config),
        Path("rodada_rline/Line_Source_Inputs.txt"): build_line_source_inputs(
            config, meteorology_path=rline_meteorology_path
        ),
        Path("metadados.txt"): build_metadata(config),
    }


def _normalise_model_text(content: str) -> tuple[tuple[str, ...], ...]:
    lines: list[tuple[str, ...]] = []
    for line in content.splitlines():
        tokens: list[str] = []
        for token in line.split():
            try:
                value = Decimal(token)
            except InvalidOperation:
                tokens.append(token)
            else:
                tokens.append(format(value.normalize(), "f"))
        lines.append(tuple(tokens))
    return tuple(lines)


def _model_input_files(
    config: CaseConfig,
    *,
    aermod_title: str | None = None,
    rline_meteorology_path: str = "./ONSITE.SFC",
) -> dict[Path, str]:
    return {
        relative: content
        for relative, content in generated_case_files(
            config,
            aermod_title=aermod_title,
            rline_meteorology_path=rline_meteorology_path,
        ).items()
        if relative != Path("metadados.txt")
    }


def validate_generated_case_inputs(
    case_dir: str | Path,
    config: CaseConfig,
    *,
    aermod_title: str | None = None,
    rline_meteorology_path: str = "./ONSITE.SFC",
) -> None:
    """Require model inputs to match the declared configuration and file layout."""

    directory = Path(case_dir)
    for relative, expected in _model_input_files(
        config,
        aermod_title=aermod_title,
        rline_meteorology_path=rline_meteorology_path,
    ).items():
        path = directory / relative
        try:
            actual = path.read_text(encoding="utf-8")
        except OSError as error:
            raise PipelineValidationError(f"input gerado ausente ou ilegivel: {path}") from error
        if _normalise_model_text(actual) != _normalise_model_text(expected):
            raise PipelineValidationError(
                f"input gerado nao corresponde ao config.json atual: {path}"
            )


def _invalidate_derived_results(case_dir: Path) -> None:
    patterns = (
        "rodada_aermod/RLINE_TEST.INP",
        "rodada_aermod/ONSITE.SFC",
        "rodada_aermod/ONSITE.PFL",
        "rodada_aermod/*.out",
        "rodada_aermod/CONC_PLOT.PLT",
        "rodada_rline/ONSITE.SFC",
        "rodada_rline/Output_*_Numerical*.csv",
        "graficos/*.png",
        "resumo.txt",
    )
    for pattern in patterns:
        for path in case_dir.glob(pattern):
            if path.is_file() or path.is_symlink():
                path.unlink()


def generate_case(config_path: str | Path, *, output_dir: str | Path | None = None) -> CaseConfig:
    """Validate JSON, atomically regenerate inputs and invalidate stale results."""

    source = Path(config_path)
    config = load_case_config(source)
    case_dir = Path(output_dir) if output_dir is not None else source.resolve().parent

    control_dir = case_dir / "controles_aermod"
    aermod_dir = case_dir / "rodada_aermod"
    rline_dir = case_dir / "rodada_rline"
    graphics_dir = case_dir / "graficos"
    for directory in (control_dir, aermod_dir, rline_dir, graphics_dir):
        directory.mkdir(parents=True, exist_ok=True)

    generated = generated_case_files(config)
    try:
        inputs_changed = any(
            not (case_dir / relative).is_file()
            or _normalise_model_text((case_dir / relative).read_text(encoding="utf-8"))
            != _normalise_model_text(content)
            for relative, content in _model_input_files(config).items()
        )
    except OSError as error:
        raise PipelineValidationError(f"falha ao comparar inputs em {case_dir}: {error}") from error

    try:
        with tempfile.TemporaryDirectory(prefix=".case-inputs.", dir=case_dir) as temporary:
            staging = Path(temporary)
            mappings: list[tuple[Path, Path]] = []
            for relative, content in generated.items():
                staged = staging / relative
                staged.parent.mkdir(parents=True, exist_ok=True)
                staged.write_text(content, encoding="utf-8", newline="\n")
                mappings.append((staged, case_dir / relative))
            if inputs_changed:
                _invalidate_derived_results(case_dir)
            publish_file_set(mappings)
    except OSError as error:
        raise PipelineValidationError(
            f"falha ao regenerar inputs em {case_dir}: {error}"
        ) from error
    return config
