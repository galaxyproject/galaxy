import logging
import logging.config
import os

# This is done in paster or galaxy.main for server app, provide
# an entry point testing as well.
logging_config = os.environ.get("GALAXY_TEST_LOGGING_CONFIG", None)
logging_config_file = None
if logging_config:
    logging_config_file = os.path.abspath(logging_config)
    logging.config.fileConfig(
        logging_config_file,
        dict(__file__=logging_config_file, here=os.path.dirname(logging_config_file)),
    )
