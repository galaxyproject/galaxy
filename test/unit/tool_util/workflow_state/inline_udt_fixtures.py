"""Shared loaders for the on-disk inline-UDT workflow fixtures.

The fixtures live at ``fixtures/inline_udt/`` (beside this module) and embed the same
``cat_user_defined`` UDT body that ``test/functional/tools/cat_user_defined.yml``
defines, so a fixture written for offline workflow_state validation has the
same shape Galaxy would emit on export.

Loaders accept an optional ``state`` override so tests that need a malformed
``tool_state`` / ``state`` can mutate one field without forking a whole new
fixture file.
"""

import json
import os
from copy import deepcopy
from typing import (
    Any,
    Dict,
    Optional,
)

import yaml

INLINE_UDT_FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "inline_udt")

NATIVE_FIXTURE_PATH = os.path.join(INLINE_UDT_FIXTURE_DIR, "cat_udt_native.ga")
FORMAT2_FIXTURE_PATH = os.path.join(INLINE_UDT_FIXTURE_DIR, "cat_udt_format2.gxwf.yml")


def load_native_inline_udt(
    state: Optional[Dict[str, Any]] = None,
    representation: Optional[Dict[str, Any]] = None,
) -> dict:
    """Load the native cat-UDT workflow; optionally swap step 1's
    ``tool_state`` or ``tool_representation`` for variant tests."""
    with open(NATIVE_FIXTURE_PATH) as fh:
        wf = json.load(fh)
    if state is not None:
        wf["steps"]["1"]["tool_state"] = deepcopy(state)
    if representation is not None:
        wf["steps"]["1"]["tool_representation"] = deepcopy(representation)
    return wf


def load_format2_inline_udt(
    state: Optional[Dict[str, Any]] = None,
    representation: Optional[Dict[str, Any]] = None,
) -> dict:
    """Load the format2 cat-UDT workflow; optionally swap ``the_udt.state``
    or ``the_udt.run`` for variant tests."""
    with open(FORMAT2_FIXTURE_PATH) as fh:
        wf = yaml.safe_load(fh)
    if state is not None:
        wf["steps"]["the_udt"]["state"] = deepcopy(state)
    if representation is not None:
        wf["steps"]["the_udt"]["run"] = deepcopy(representation)
    return wf


def cat_udt_body() -> dict:
    """Return a fresh deep copy of the cat-UDT tool body itself.

    Used by tests that build degenerate variants (admin-class, malformed
    citation, etc.) by mutating individual fields of the body.
    """
    return deepcopy(load_native_inline_udt()["steps"]["1"]["tool_representation"])
