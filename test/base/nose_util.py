""" Utilities for dealing with nose.

There was some duplication between Galaxy, Tool Shed, and Install/Test,
trying to reduce that here.
"""

import nose


def run( test_config, plugins=[] ):
    loader = nose.loader.TestLoader( config=test_config )
    for plugin in plugins:
        test_config.plugins.addPlugin( plugin )
    plug_loader = test_config.plugins.prepareTestLoader( loader )
    if plug_loader is not None:
        loader = plug_loader
    tests = loader.loadTestsFromNames( test_config.testNames )
    test_runner = nose.core.TextTestRunner(
        stream=test_config.stream,
        verbosity=test_config.verbosity,
        config=test_config
    )
    plug_runner = test_config.plugins.prepareTestRunner( test_runner )
    if plug_runner is not None:
        test_runner = plug_runner
    result = test_runner.run( tests )
    return result
