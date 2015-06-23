"""
OMERO Image Fetching Tool.

Usage:
  omero_fetch.py <tsv_input> --output_files_path=<path> --history_id=<id>

Options:
  -h --help                   Show this screen.
  --output_files_path=<path>  Path to the "files_path" for the resulting HTML.
  --history_id=<id>           The current history where images will be written to.
"""

from PIL import Image
from StringIO import StringIO
from docopt import docopt
import json
import pandas as pd
import requests
import sys
import time
import os.path
import httplib

omero_login_payload = {
    "username":  "client",
    "password":  "bigdata",
    "server":    "1"
}

def login(host=None):

    session = requests.session()

    response = None

    while response is None or response.status_code != 200:

        try:
            response = session.get("{0}/webclient/login".format(host), params=omero_login_payload)

        except requests.exceptions.ConnectionError:
            print("Connection Error with OMERO Server: {0}".format(host))
            sys.exit(1) 

        except requests.exceptions.ChunkedEncodingError:
            print("Chunked Encoding Error: {0}".format(host))
            time.sleep(1.0)
	
	except httplib.IncompleteRead:
	    print("Incomplete Read with OMERO Server: {0}".format(host))
	    time.sleep(1.0)
    
    return session


def download_thumbnail(image_id, prefix=None, host=None, session=None, files_path=None):

      response = session.get("{0}webgateway/render_thumbnail/{1}/".format(host, image_id))

      image = Image.open(StringIO(response.content))

      image.save(os.path.join(files_path, "data/images/{0}.jpg".format(prefix)))


def create_json(tsv_file_path, history_id=None, output_files_path=None):

    sessions = {}

    try:
        data = pd.read_csv(tsv_file_path, sep="\t")

    except IOError:
        print("Could not open input file {0}".format(tsv_file_path))
        sys.exit(1)

    # Assign the thumbnailUrl using CCC_DID
    data["thumbnailUrl"] = data.cccDid.apply(lambda x: "data/images/{0}.jpg".format(x))

    for index, row in data.iterrows():

        host = row.omeroHost

        if host not in sessions:
            sessions[host] = login(host)

        session = sessions[host]

        download_thumbnail(
                row.omeroImageId,
                prefix=row.cccDid,
                host=row.omeroHost,
                session=session,
                files_path=output_files_path)

    payload =  {
      "galaxy": {
          "historyId": history_id },
      "images": json.loads(data.to_json(orient="records"))
    }

    output_json_path = os.path.join(output_files_path, "data/images.json")

    with open(output_json_path, "w") as json_file:
        json.dump(payload, json_file)

if __name__ == "__main__":
    arguments = docopt(__doc__, version="0.0.1")

    tsv_file_path = arguments["<tsv_input>"]
    history_id = arguments["--history_id"]
    output_files_path = arguments["--output_files_path"]

    create_json(tsv_file_path, history_id=history_id, output_files_path=output_files_path)
