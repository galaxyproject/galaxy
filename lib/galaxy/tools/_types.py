"""
Tool state goes through several different iterations that are difficult to follow I think,
hopefully datatypes can be used as markers to describe what has been done - even if they don't
provide strong traditional typing semantics.

+--------------------------------+------------+---------------------------------+------------+-----------+
| Python Type                    | State for? | Object References               | Validated? | xref      |
+================================+============+=================================+============+===========+
| ToolRequestT                   | request    | src dicts of encoded ids        | nope        |          |
| ToolStateJobInstanceT          | a job      | src dicts of encoded ids        | nope        |          |
| ToolStateJobInstanceExpansionT | a job      | a mix I think, things that were | nope        |          |
|                                |            | expanded are objects            | nope        |          |
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
    Union,
)

from typing_extensions import Literal

# Input dictionary from the API, may include map/reduce instructions. Objects are referenced by "src"
# dictionaries and encoded IDS.
ToolRequestT = dict[str, Any]

# Input dictionary extracted from a tool request for running a tool individually as a single job. Objects are referenced
# by "src" dictionaries with encoded IDs still but batch instructions have been pulled out. Parameters have not
# been "checked" (check_param has not been called).
ToolStateJobInstanceT = dict[str, Any]

# After meta.expand_incoming stuff I think expanded parameters are in model object form but the other stuff is likely
# still encoded IDs? None of this is verified though.
ToolStateJobInstanceExpansionT = dict[str, Any]

# Input dictionary for an individual job where objects are their model objects and parameters have been
# "checked" (check_param has been called).
ToolStateJobInstancePopulatedT = dict[str, Any]

# Input dictionary for an individual where the state has been valiated and populated but then converted back down
# to json. Object references are unified in the format of {"values": List["src" dictionary]} where the src dictionaries.
# are decoded ids (ints).
# See comments on galaxy.tools.parameters.params_to_strings for more information.
ToolStateDumpedToJsonInternalT = dict[str, Any]

# Input dictionary for an individual where the state has been valiated and populated but then converted back down
# to json. Object references are unified in the format of {"values": List["src" dictionary]} where src dictonaries
# are encoded (ids). See comments on galaxy.tools.parameters.params_to_strings for more information.
ToolStateDumpedToJsonT = dict[str, Any]

# Input dictionary for an individual where the state has been valiated and populated but then converted back down
# to json. Object references are unified in the format of {"values": List["src" dictionary]} but dumped into
# strings. See comments on galaxy.tools.parameters.params_to_strings for more information. This maybe should be
# broken into separate types for encoded and decoded IDs in subsequent type refinements if both are used, it not
# this comment should be updated to indicate which is used exclusively.
ToolStateDumpedToStringsT = dict[str, str]

# A dictionary of error messages that occur while attempting to validate a ToolStateJobInstanceT and transform it
# into a ToolStateJobInstancePopulatedT with model objects populated. Tool errors indicate the job should not be
# further processed.
ParameterValidationErrorsT = dict[str, Union["ParameterValidationErrorsT", str, Exception]]

InputFormatT = Literal["legacy", "21.01"]
