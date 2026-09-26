"""Guard that the mirrored HashFunctionNames in tool_util_models stays in sync
with galaxy.util.hash_util. The mirror exists so the package has no runtime
dep on galaxy.util; this test lives here (not in test/unit/tool_util_models/)
so it runs in the monorepo env where galaxy.util is importable.
"""

from typing import get_args

from galaxy.tool_util_models.test_job import HashFunctionNames as MirroredHashFunctionNames
from galaxy.util.hash_util import HashFunctionNames


def test_hash_function_names_in_sync():
    assert get_args(MirroredHashFunctionNames) == get_args(HashFunctionNames)
