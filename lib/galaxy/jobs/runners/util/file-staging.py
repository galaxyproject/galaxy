import os
import sys

from pulsar.client.transport import post_file


def get_job_directory_files(work_dir: str):
    """
    Get path for all the files from work directory
    """
    paths = []
    for root, _, files in os.walk(work_dir):
        for file in files:
            paths.append(os.path.join(root, file))

    return paths


def stage_back_data(url, paths):
    """Responsible for staging out of data for the desired path"""

    for file_path in paths:
        temp_url = f"{url}&path={file_path}"
        try:
            post_file(temp_url, file_path)
        except Exception:
            sys.stderr.write("Unable to reach the defined URL from TES Container")
            exit(1)


if __name__ == "__main__":
    url = sys.argv[1]
    work_dir = sys.argv[2]
    work_dir_files = get_job_directory_files(work_dir)
    n = len(sys.argv)
    paths = [sys.argv[i] for i in range(3, n)]
    paths.extend(work_dir_files)
    stage_back_data(url, paths)
