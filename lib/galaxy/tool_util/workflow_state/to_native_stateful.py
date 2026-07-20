"""Convert format2 workflows to native Galaxy format with schema-aware state encoding.

gxformat2's to_native() handles structural conversion (steps, connections,
tool_state). When given a state_encode_to_native callback via ConversionOptions,
it produces correctly-typed native tool_state using tool definitions — reversing
format2 conveniences like list→comma-string for multiple selects. This module
wires that callback with per-step tracking and strict mode.
"""

import json
import logging
import os
import sys
from dataclasses import (
    dataclass,
    field,
)
from typing import (
    List,
    Optional,
)

from gxformat2.normalized import (
    NormalizedNativeWorkflow,
    to_native,
)
from gxformat2.options import ConversionOptions
from gxformat2.yaml import ordered_load_path

from ._cli_common import (
    setup_tool_info,
    ToolCacheOptions,
)
from ._types import GetToolInfo
from .convert import make_encode_tool_state

log = logging.getLogger(__name__)


@dataclass
class StepEncodeStatus:
    step_id: str
    step_label: Optional[str] = None
    tool_id: Optional[str] = None
    encoded: bool = False
    error: Optional[str] = None


@dataclass
class ToNativeResult:
    native: NormalizedNativeWorkflow
    steps: List[StepEncodeStatus] = field(default_factory=list)

    @property
    def native_dict(self) -> dict:
        return self.native.to_dict()

    @property
    def all_encoded(self) -> bool:
        return all(s.encoded for s in self.steps)

    @property
    def failed_steps(self) -> List[StepEncodeStatus]:
        return [s for s in self.steps if not s.encoded]

    @property
    def summary(self) -> str:
        ok = sum(1 for s in self.steps if s.encoded)
        fail = len(self.steps) - ok
        return f"{ok} schema-encoded, {fail} fell back to default"


def convert_to_native_stateful(
    workflow_path: str,
    get_tool_info: GetToolInfo,
    strict: bool = False,
) -> ToNativeResult:
    """Convert format2 workflow to native with schema-aware tool_state encoding.

    Requires format2 input — native .ga files are rejected because
    ensure_native() would short-circuit and skip the encoder callback.

    Conversion happens inside to_native() via the state_encode_to_native
    callback. Steps where encoding fails keep default json.dumps encoding
    unless strict=True.
    """
    workflow_dict = ordered_load_path(workflow_path)
    if isinstance(workflow_dict, dict) and workflow_dict.get("a_galaxy_workflow") == "true":
        raise EncodeError(
            f"{workflow_path} is already native format. "
            "Use gxwf-to-format2-stateful to convert native→format2, "
            "or gxwf-roundtrip-validate for native→format2→native validation."
        )

    step_statuses: List[StepEncodeStatus] = []
    callback = _make_encode_callback(get_tool_info, step_statuses, strict=strict)

    options = ConversionOptions(
        state_encode_to_native=callback,
        workflow_directory=os.path.dirname(os.path.abspath(workflow_path)),
    )
    native = to_native(workflow_dict, options=options)

    return ToNativeResult(native=native, steps=step_statuses)


def _make_encode_callback(
    get_tool_info: GetToolInfo,
    step_statuses: List[StepEncodeStatus],
    strict: bool = False,
):
    """Build a state_encode_to_native callback with status tracking."""
    base_encoder = make_encode_tool_state(get_tool_info)
    step_counter = [0]

    def _encode(step: dict, state: dict):
        step_counter[0] += 1
        tool_id = step.get("tool_id")
        step_id = str(step_counter[0])

        try:
            result = base_encoder(step, state)
            if result is not None:
                step_statuses.append(StepEncodeStatus(step_id=step_id, tool_id=tool_id, encoded=True))
                return result
            else:
                error = "no tool definition available"
                step_statuses.append(StepEncodeStatus(step_id=step_id, tool_id=tool_id, encoded=False, error=error))
                if strict:
                    raise EncodeError(f"Step {step_id} ({tool_id}): {error}")
                return None
        except EncodeError:
            raise
        except Exception as e:
            error_msg = str(e)
            step_statuses.append(StepEncodeStatus(step_id=step_id, tool_id=tool_id, encoded=False, error=error_msg))
            if strict:
                raise EncodeError(f"Step {step_id} ({tool_id}): {error_msg}") from e
            log.debug("Step %s (%s): encoding failed, using default: %s", step_id, tool_id, error_msg)
            return None

    return _encode


class EncodeError(Exception):
    pass


# -- Options model --


class ToNativeOptions(ToolCacheOptions):
    output: Optional[str] = None
    strict: bool = False


# -- Formatters --


def format_summary(result: ToNativeResult) -> str:
    lines = []
    for s in result.steps:
        tool_label = s.tool_id or "?"
        if s.encoded:
            lines.append(f"Step {s.step_id}: {tool_label} ... OK")
        else:
            lines.append(f"Step {s.step_id}: {tool_label} ... FALLBACK ({s.error})")
    lines.append("---")
    lines.append(result.summary)
    return "\n".join(lines)


def format_native_json(native_dict: dict) -> str:
    return json.dumps(native_dict, indent=4) + "\n"


# -- Entry point --


def run_to_native(options: ToNativeOptions) -> int:
    """Run format2→native conversion pipeline. Returns exit code."""
    tool_info = setup_tool_info(options)

    try:
        result = convert_to_native_stateful(
            options.workflow_path,
            tool_info,
            strict=options.strict,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    output = format_native_json(result.native_dict)

    if options.output:
        os.makedirs(os.path.dirname(os.path.abspath(options.output)), exist_ok=True)
        with open(options.output, "w") as f:
            f.write(output)
        print(format_summary(result), file=sys.stderr)
    else:
        print(format_summary(result), file=sys.stderr)
        sys.stdout.write(output)

    return 1 if result.failed_steps else 0
