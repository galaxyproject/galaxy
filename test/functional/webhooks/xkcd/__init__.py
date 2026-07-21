import json
import logging
import random
from urllib.request import urlopen

log = logging.getLogger(__name__)


def main(trans, webhook, params):
    error = ""
    comic = {}

    try:
        # The xkcd JSON API has no CORS headers and info.0.json is only served
        # over HTTPS, so fetch it server-side rather than from the browser.
        latest = json.loads(urlopen("https://xkcd.com/info.0.json").read())
        random_id = random.randint(1, latest["num"])
        data = json.loads(urlopen(f"https://xkcd.com/{random_id}/info.0.json").read())
        comic = {"img": data["img"], "alt": data["alt"], "title": data["title"]}
    except Exception as e:
        log.exception(e)
        error = str(e)

    return {"success": not error, "error": error, "comic": comic}
