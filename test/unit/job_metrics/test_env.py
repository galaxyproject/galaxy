from galaxy.job_metrics.instrumenters.env import EnvPlugin
from .test_core import _run_plugin

TEST_ENV = {
    "FOOBAR": "moocow",
    "DOGCAT": "catdog",
}


def test_env_instrumentation(tmpdir):
    env_plugin = EnvPlugin()
    _run_plugin(env_plugin, tmpdir, TEST_ENV)
    props = env_plugin.job_properties(1, tmpdir)
    assert props
    assert props["FOOBAR"] == "moocow"
    assert props["DOGCAT"] == "catdog"


def test_env_restrict_variables(tmpdir):
    env_plugin = EnvPlugin(
        variables="FOOBAR,FOOBAR2",
    )
    _run_plugin(env_plugin, tmpdir, TEST_ENV)
    props = env_plugin.job_properties(1, tmpdir)
    assert props
    assert props["FOOBAR"] == "moocow"
    assert "DOGCAT" not in props
