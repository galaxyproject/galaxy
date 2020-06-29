from locust import HttpUser, task, between
import subprocess

# In order to run the load tests, the following environment variables must be set:
#
# GALAXY_TEST_EXTERNAL
#   - This is the URL of server that is being load tested. Tests run against this server.
#   - Example value: "http://127.0.0.1:8081"
# GALAXY_CONFIG_MASTER_API_KEY
#   - The value comes from 'master_api_key' in 'galaxy.yml' configuration file of the server that is being load tested
#   - Example value = "abcdefg"


class ObjectStoreLoadTest(HttpUser):
    wait_time = between(1, 2)

    # Relative path to Galaxy root folder
    GALAXY_HOME = "../../.."
    run_tests_script = "%s/run_tests.sh" % (GALAXY_HOME)

    @task
    def upload_download_delete_random_file(self):
        command = subprocess.run(["sh", self.run_tests_script, "-api", "./lib/galaxy_test/api/test_tools_upload.py::ToolsUploadTestCase::test_upload_download_delete_of_randomly_generated_file"])
        if command.returncode == 0:
            print("Exit code was 0")
        else:
            print("Exit code was NOT 0")
