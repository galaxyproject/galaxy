import time
import json

MAX_RETRY_COUNT = 5
RETRY_SLEEP_TIME = 0.1


class parseJson(object):

    def __call__(self, func):
        def replacement(*args, **kwargs):
            response = func(*args, **kwargs)
            return json.loads(response)
        return replacement


class retry(object):

    def __call__(self, func):

        def replacement(*args, **kwargs):
            max_count = MAX_RETRY_COUNT
            count = 0
            while True:
                count += 1
                try:
                    return func(*args, **kwargs)
                except:
                    if count >= max_count:
                        raise
                    else:
                        time.sleep(RETRY_SLEEP_TIME)
                        continue

        return replacement
