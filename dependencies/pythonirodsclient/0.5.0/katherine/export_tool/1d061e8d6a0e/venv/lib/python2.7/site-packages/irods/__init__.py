import logging

# iRODS settings
IRODS_VERSION = {'major': 4, 'minor': 1, 'patchlevel': 6, 'api': 'd'}

# Magic Numbers
MAX_PASSWORD_LENGTH = 50
MAX_SQL_ATTR = 50
MAX_PATH_ALLOWED = 1024
MAX_NAME_LEN = MAX_PATH_ALLOWED + 64
RESPONSE_LEN = 16
CHALLENGE_LEN = 64

# Logging
logger = logging.getLogger()
logger.setLevel(logging.ERROR)
h = logging.StreamHandler()
f = logging.Formatter(
    "%(asctime)s %(name)s-%(levelname)s [%(pathname)s %(lineno)d] %(message)s")
h.setFormatter(f)
logger.addHandler(h)
