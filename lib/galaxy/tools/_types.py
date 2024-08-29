"""
Tool state goes through several different iterations that are difficult to follow I think,
hopefully datatypes can be used as markers to describe what has been done - even if they don't
provide strong traditional typing semantics.

+--------------------------------+------------+---------------------------------+------------+-----------+
| Python Type                    | State for? | Object References               | Validated? | xref      |
+================================+============+=================================+============+===========+
| ToolRequestT                   | request    | src dicts of encoded ids        | nope        |          |
| ToolStateJobInstanceT          | a job      | src dicts of encoded ids        | nope        |          |
| ToolStateJobInstancePopulatedT | a job      | model objs loaded from db       | check_param |          |
| ToolStateDumpedToJsonT         | a job      | src dicts of encoded ids        | "           |          |
|                                |            | (normalized into values attr)   | "           |          |
| ToolStateDumpedToJsonInternalT | a job      | src dicts of decoded ids        | "           |          |
|                                |            | (normalized into values attr)   | "           |          |
| ToolStateDumpedToStringsT      | a job      | src dicts dumped to strs        | "           |          |
|                                |            | (normalized into values attr)   | "           |          |
+--------------------------------+------------+---------------------------------+-------------+----------+
"""

from typing import (
    Any,
    Dict,
    Union,
)

from typing_extensions import Literal

# Input dictionary from the API, may include map/reduce instructions. Objects are referenced by "src"
# dictionaries and encoded IDS.
ToolRequestT = Dict[str, Any]

# Input dictionary extracted from a tool request for running a tool individually as a single job. Objects are referenced
# by "src" dictionaries with encoded IDs still but batch instructions have been pulled out. Parameters have not
# been "checked" (check_param has not been called).
ToolStateJobInstanceT = Dict[str, Any]

# Input dictionary for an individual job where objects are their model objects and parameters have been
# "checked" (check_param has been called).
ToolStateJobInstancePopulatedT = Dict[str, Any]

# Input dictionary for an individual where the state has been valiated and populated but then converted back down
# to json. Object references are unified in the format of {"values": List["src" dictionary]} where the src dictionaries.
# are decoded ids (ints).
# See comments on galaxy.tools.parameters.params_to_strings for more information.
ToolStateDumpedToJsonInternalT = Dict[str, Any]

# Input dictionary for an individual where the state has been valiated and populated but then converted back down
# to json. Object references are unified in the format of {"values": List["src" dictionary]} where src dictonaries
# are encoded (ids). See comments on galaxy.tools.parameters.params_to_strings for more information.
ToolStateDumpedToJsonT = Dict[str, Any]

# Input dictionary for an individual where the state has been valiated and populated but then converted back down
# to json. Object references are unified in the format of {"values": List["src" dictionary]} but dumped into
# strings. See comments on galaxy.tools.parameters.params_to_strings for more information. This maybe should be
# broken into separate types for encoded and decoded IDs in subsequent type refinements if both are used, it not
# this comment should be updated to indicate which is used exclusively.
ToolStateDumpedToStringsT = Dict[str, str]

# A dictionary of error messages that occur while attempting to validate a ToolStateJobInstanceT and transform it
# into a ToolStateJobInstancePopulatedT with model objects populated. Tool errors indicate the job should not be
# further processed.
ParameterValidationErrorsT = Dict[str, Union["ParameterValidationErrorsT", str, Exception]]

InputFormatT = Literal["legacy", "21.01"]
