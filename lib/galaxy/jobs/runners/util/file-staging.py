import sys
from pulsar.client.transport import post_file


def stage_back_data(url, paths):
    """Responsible for staging out of data for the desired path"""

    # Handling localhost cases
    url = url.replace("127.0.0.1", str("172.17.0.1"))
    url = url.replace("localhost", str("172.17.0.1"))

    for file_path in paths:
        temp_url = url + '&path=' + file_path
        post_file(temp_url, file_path)

if __name__=="__main__":
    url = sys.argv[1]
    n = len(sys.argv)
    paths = [sys.argv[i] for i in range(2, n)]
    stage_back_data(url, paths)