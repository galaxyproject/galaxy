"""Manager for versioned storage of agent evaluation reports."""
import fcntl
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .file_utils import atomic_json_write

log = logging.getLogger(__name__)


class ReportManager:
    """Manages versioned storage of agent evaluation reports.

    Organizes reports by run ID with category subdirectories, generates
    summary statistics, and maintains a symlink to the latest run.

    Directory structure:
        database/agent_eval_reports/
        ├── runs/
        │   ├── 20260212_231045_sonnet45/
        │   │   ├── metadata.json
        │   │   ├── bioinformatics_workflows/
        │   │   │   ├── test_scrna_cell_type_identification.json
        │   │   │   └── ...
        │   │   ├── routing/
        │   │   └── summary.json
        │   └── ...
        └── latest -> runs/20260212_231045_sonnet45/
    """

    def __init__(
        self,
        run_id: str,
        agent_model: str,
        judge_model: str,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize ReportManager.

        Args:
            run_id: Unique identifier for this test run
            agent_model: Model used for agent responses
            judge_model: Model used for evaluation
            config: Optional configuration dict to store in metadata
        """
        log.debug(f"Initializing ReportManager for run {run_id}")
        self.run_id = run_id
        self.agent_model = agent_model
        self.judge_model = judge_model
        self.config = config or {}

        # Set up directory structure
        self.base_dir = Path("database/agent_eval_reports")
        self.run_dir = self.base_dir / "runs" / run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # Save run metadata
        self._save_metadata()

    def _save_metadata(self) -> None:
        """Save run metadata to metadata.json.

        Raises:
            OSError: If unable to write metadata file
        """
        metadata = {
            "run_id": self.run_id,
            "timestamp": time.time(),
            "timestamp_str": time.strftime("%Y-%m-%d %H:%M:%S"),
            "agent_model": self.agent_model,
            "judge_model": self.judge_model,
            "config": self.config
        }

        metadata_file = self.run_dir / "metadata.json"
        try:
            atomic_json_write(metadata_file, metadata)
            log.debug(f"Saved metadata for run {self.run_id}")
        except OSError as e:
            log.exception(f"Failed to save metadata: {e}")
            raise

    def save_report(
        self,
        category: str,
        test_name: str,
        report_data: Dict[str, Any]
    ) -> None:
        """Save test report to category subdirectory.

        Args:
            category: Test category (e.g., "bioinformatics_workflows")
            test_name: Name of the test
            report_data: Complete report data dict

        Raises:
            OSError: If unable to write report file
        """
        log.info(f"Saving report: {category}/{test_name}")

        # Create category directory if it doesn't exist
        category_dir = self.run_dir / category
        category_dir.mkdir(exist_ok=True)

        # Save report atomically
        report_file = category_dir / f"{test_name}.json"
        try:
            atomic_json_write(report_file, report_data)
        except OSError as e:
            log.exception(f"Failed to save report {test_name}: {e}")
            raise

    def finalize(self) -> None:
        """Generate summary and update 'latest' symlink.

        Call this after all tests have completed.
        Uses file locking to prevent race conditions when multiple
        test sessions finalize concurrently.

        Raises:
            OSError: If unable to write summary or update symlink
        """
        log.info(f"Finalizing report for run {self.run_id}")

        # Generate summary statistics
        summary = self._generate_summary()
        summary_file = self.run_dir / "summary.json"

        try:
            atomic_json_write(summary_file, summary)
            log.debug("Saved summary.json")
        except OSError as e:
            log.exception(f"Failed to save summary: {e}")
            raise

        # Update 'latest' symlink with file locking to prevent race conditions
        self._update_latest_symlink()

    def _update_latest_symlink(self) -> None:
        """Atomically update 'latest' symlink with file locking.

        Uses exclusive file lock to prevent race conditions when
        multiple test sessions try to update the symlink concurrently.

        Raises:
            OSError: If unable to create/update symlink
        """
        lock_file = self.base_dir / ".latest.lock"
        latest_link = self.base_dir / "latest"

        try:
            # Acquire exclusive lock (blocks until available)
            with open(lock_file, 'w') as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                log.debug("Acquired lock for symlink update")

                # Remove existing symlink if present
                if latest_link.exists() or latest_link.is_symlink():
                    latest_link.unlink()

                # Create new symlink
                latest_link.symlink_to(f"runs/{self.run_id}")
                log.info(f"Updated 'latest' symlink to {self.run_id}")

                # Lock released automatically on file close

        except OSError as e:
            log.exception(f"Failed to update symlink: {e}")
            raise

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate aggregated statistics for this run.

        Returns:
            Dict with summary statistics including totals and per-category breakdowns
        """
        log.debug("Generating summary statistics")
        summary = {
            "run_id": self.run_id,
            "timestamp": time.time(),
            "agent_model": self.agent_model,
            "judge_model": self.judge_model,
            "categories": {},
            "totals": {
                "tests": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
                "total_cost": 0.0,
                "total_duration_ms": 0,
                "avg_quality_score": None
            }
        }

        total_tests = 0
        total_passed = 0
        total_cost = 0.0
        total_duration = 0
        quality_scores = []

        # Scan all category directories
        for category_dir in self.run_dir.iterdir():
            if not category_dir.is_dir() or category_dir.name in ["metadata.json", "summary.json"]:
                continue

            category_name = category_dir.name
            category_stats = {
                "tests": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0
            }

            # Process each test report in this category
            for test_file in category_dir.glob("*.json"):
                try:
                    with open(test_file) as f:
                        report = json.load(f)

                    # Validate report has required fields
                    if not self._validate_report(report):
                        log.warning(f"Skipping invalid report: {test_file}")
                        continue

                    category_stats["tests"] += 1
                    total_tests += 1

                    if report.get("status") == "PASSED":
                        category_stats["passed"] += 1
                        total_passed += 1
                    else:
                        category_stats["failed"] += 1

                    # Aggregate metrics
                    total_cost += report.get("cost", 0.0)
                    total_duration += report.get("duration_ms", 0)

                    if "quality_score" in report:
                        quality_scores.append(report["quality_score"])

                except (json.JSONDecodeError, OSError) as e:
                    log.warning(f"Failed to load report {test_file}: {e}")
                    continue

            # Calculate category pass rate
            if category_stats["tests"] > 0:
                category_stats["pass_rate"] = category_stats["passed"] / category_stats["tests"]

            summary["categories"][category_name] = category_stats

        # Calculate overall statistics
        summary["totals"]["tests"] = total_tests
        summary["totals"]["passed"] = total_passed
        summary["totals"]["failed"] = total_tests - total_passed
        if total_tests > 0:
            summary["totals"]["pass_rate"] = total_passed / total_tests
        summary["totals"]["total_cost"] = round(total_cost, 4)
        summary["totals"]["total_duration_ms"] = total_duration
        if quality_scores:
            summary["totals"]["avg_quality_score"] = round(sum(quality_scores) / len(quality_scores), 3)

        return summary

    @staticmethod
    def _validate_report(report: Dict[str, Any]) -> bool:
        """Validate that report has required fields.

        Args:
            report: Report dictionary to validate

        Returns:
            True if report is valid, False otherwise
        """
        required_fields = ["test_name", "status", "duration_ms", "cost"]
        return all(field in report for field in required_fields)
