import argparse
import os
import shutil
import sys

THIS_DIRECTORY = os.path.dirname(__file__)

parser = argparse.ArgumentParser(
    prog="search_for_new_screenshots",
    description="Searches a Selenium screenshot directory for screenshots used in the admin docs and grabs new ones if available",
)

SEARCH_FOR = [
    "user_object_store_form_empty_azure.png",
    "user_object_store_form_full_azure.png",
    "user_object_store_form_empty_generic_s3.png",
    "user_object_store_form_full_generic_s3.png",
    "user_object_store_form_empty_aws_s3.png",
    "user_object_store_form_full_aws_s3.png",
    "user_object_store_form_empty_gcp_s3_interop.png",
    "user_object_store_form_full_gcp_s3_interop.png",
    "user_file_source_form_full_aws_public.png",
    "user_file_source_form_full_azure.png",
    "user_file_source_form_full_ftp.png",
    "user_file_source_form_full_webdav.png",
    "user_file_source_form_full_elabftw.png",
]


def main(argv):
    parser.add_argument("screenshot_directory")
    args = parser.parse_args(argv[1:])
    screenshot_directory = args.screenshot_directory
    for filename in os.listdir(screenshot_directory):
        if filename in SEARCH_FOR:
            print(f"Found useful screenshot {filename}, copying to {THIS_DIRECTORY}")
            shutil.copy(os.path.join(screenshot_directory, filename), os.path.join(THIS_DIRECTORY, filename))


if __name__ == "__main__":
    main(sys.argv)
