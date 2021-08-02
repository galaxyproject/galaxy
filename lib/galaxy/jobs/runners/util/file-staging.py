import sys
from pulsar.client.transport import post_file


def stage_back_data(url, paths):
    """Responsible for staging out of data for the desired path"""

    url = url.replace("localhost", str("172.17.0.1"))

    for file_path in paths:
        temp_url = url + '&path=' + file_path
        try:
            post_file(temp_url, file_path)
        except:
            sys.stderr.write("Unable to reach the defined URL from TES Container")
            exit(1)

if __name__=="__main__":
    url = sys.argv[1]
    n = len(sys.argv)
    paths = [sys.argv[i] for i in range(2, n)]
    stage_back_data(url, paths)