"""Integration test for a job that the embedded Pulsar's batch system reports as failed."""

import os
import shutil
import stat
import tempfile

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
EMBEDDED_PULSAR_FAILED_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_failed_job_conf.yml")
OOM_KILL_MESSAGE = "slurmstepd: error: Detected 1 oom-kill event(s)"

# Runs the batch script in the background and, like Slurm's cgroup OOM killer, reports a job that
# exited non-zero as failed (state F) with a slurmstepd line in the job's stderr.
FAKE_SBATCH = f"""#!/bin/sh
script="$1"
out=$(sed -n 's/^#SBATCH -o //p' "$script")
err=$(sed -n 's/^#SBATCH -e //p' "$script")
state="$(dirname "$0")/jobs/$$"
mkdir -p "$state"
(
    sh "$script" > "$out" 2> "$err"
    return_code=$(cat "$(dirname "$script")/return_code")
    if [ "$return_code" != 0 ]; then
        echo "{OOM_KILL_MESSAGE} in StepId=$$.batch." >> "$err"
    fi
    echo "$return_code" > "$state/return_code.tmp"
    mv "$state/return_code.tmp" "$state/return_code"
) < /dev/null > /dev/null 2>&1 &
echo "Submitted batch job $$"
"""
FAKE_SQUEUE = """#!/bin/sh
for job_id; do :; done
state="$(dirname "$0")/jobs/$job_id"
echo "JOBID ST"
if [ ! -f "$state/return_code" ]; then
    echo "$job_id R"
elif [ "$(cat "$state/return_code")" != 0 ]; then
    echo "$job_id F"
fi
"""
FAKE_SCANCEL = "#!/bin/sh\n"


class TestEmbeddedPulsarFailedJobIntegration(integration_util.IntegrationTestCase):
    framework_tool_and_types = True
    dataset_populator: DatasetPopulator
    fake_slurm_directory: str
    original_path: str

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def setUpClass(cls):
        cls.fake_slurm_directory = tempfile.mkdtemp()
        for name, contents in (("sbatch", FAKE_SBATCH), ("squeue", FAKE_SQUEUE), ("scancel", FAKE_SCANCEL)):
            path = os.path.join(cls.fake_slurm_directory, name)
            with open(path, "w") as script:
                script.write(contents)
            os.chmod(path, stat.S_IRWXU)
        # Embedded Pulsar runs the batch commands in this process' environment.
        cls.original_path = os.environ["PATH"]
        os.environ["PATH"] = f"{cls.fake_slurm_directory}{os.pathsep}{cls.original_path}"
        try:
            super().setUpClass()
        except BaseException:
            cls._remove_fake_slurm()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
        finally:
            cls._remove_fake_slurm()

    @classmethod
    def _remove_fake_slurm(cls):
        os.environ["PATH"] = cls.original_path
        shutil.rmtree(cls.fake_slurm_directory, ignore_errors=True)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = EMBEDDED_PULSAR_FAILED_JOB_CONFIG_FILE
        config["job_metrics"] = [{"type": "core"}]

    def test_failed_job_keeps_streams_and_metrics(self):
        with self.dataset_populator.test_history() as history_id:
            result = self.dataset_populator.run_tool("job_properties", {"thebool": False}, history_id)
            job_id = result["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(job_id, assert_ok=False)
            job = self.dataset_populator.get_job_details(job_id, full=True).json()
            assert job["state"] == "error"
            assert job["exit_code"] == 2
            assert "The bool is not true" in job["tool_stdout"]
            assert "The bool is very not true" in job["tool_stderr"]
            assert OOM_KILL_MESSAGE in job["job_stderr"]
            metrics = self._get(f"jobs/{job_id}/metrics", admin=True).json()
            assert "runtime_seconds" in {metric["name"] for metric in metrics}
