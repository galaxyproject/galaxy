#!/usr/bin/env python
"""Generate comparison dashboard for multiple agent evaluation runs.

Compares 2-3 test runs side-by-side to evaluate:
- Model performance (pass rates, quality scores)
- Cost efficiency (total cost, cost per test)
- Test-by-test differences
- Category-level performance
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_run_data(base_dir: Path, run_id: str) -> dict[str, Any]:
    """Load metadata and all test results for a run."""
    run_dir = base_dir / "runs" / run_id

    if not run_dir.exists():
        raise ValueError(f"Run directory not found: {run_dir}")

    # Load metadata
    metadata_file = run_dir / "metadata.json"
    metadata = {}
    if metadata_file.exists():
        with open(metadata_file) as f:
            metadata = json.load(f)

    # Load all test results by category
    results_by_category = {}
    for category_dir in run_dir.iterdir():
        if not category_dir.is_dir():
            continue

        category_name = category_dir.name
        if category_name in ["metadata.json", "summary.json"]:
            continue

        category_tests = []
        for test_file in category_dir.glob("*.json"):
            with open(test_file) as f:
                category_tests.append(json.load(f))

        if category_tests:
            results_by_category[category_name] = category_tests

    # Flatten all tests
    all_tests = []
    for tests in results_by_category.values():
        all_tests.extend(tests)

    return {
        "run_id": run_id,
        "metadata": metadata,
        "results_by_category": results_by_category,
        "all_tests": all_tests,
    }


def calculate_run_stats(run_data: dict[str, Any]) -> dict[str, Any]:
    """Calculate aggregate statistics for a run."""
    tests = run_data["all_tests"]

    total = len(tests)
    passed = sum(1 for t in tests if t.get("status") == "PASSED")
    failed = total - passed

    # Cost and duration
    total_cost = sum(t.get("cost", 0.0) for t in tests)
    total_duration = sum(t.get("duration_ms", 0) for t in tests)
    avg_cost = total_cost / total if total > 0 else 0
    avg_duration = total_duration / total if total > 0 else 0

    # Quality scores (if present)
    quality_scores = [t["quality_score"] for t in tests if "quality_score" in t]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None

    return {
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / total if total > 0 else 0,
        "total_cost": total_cost,
        "avg_cost": avg_cost,
        "total_duration_ms": total_duration,
        "avg_duration_ms": avg_duration,
        "avg_quality_score": avg_quality,
    }


def find_common_tests(runs_data: list[dict[str, Any]]) -> set[str]:
    """Find tests that exist in all runs."""
    if not runs_data:
        return set()

    # Get test names from first run
    common = {t["test_name"] for t in runs_data[0]["all_tests"]}

    # Intersect with other runs
    for run_data in runs_data[1:]:
        test_names = {t["test_name"] for t in run_data["all_tests"]}
        common &= test_names

    return common


def get_test_by_name(tests: list[dict], test_name: str) -> dict | None:
    """Find a test by name in a list."""
    for test in tests:
        if test.get("test_name") == test_name:
            return test
    return None


def generate_comparison_html(runs_data: list[dict[str, Any]]) -> str:
    """Generate HTML comparison dashboard."""

    # Calculate stats for each run
    runs_stats = [calculate_run_stats(run) for run in runs_data]

    # Find common tests
    common_tests = find_common_tests(runs_data)

    # Get run labels
    run_labels = []
    for run_data in runs_data:
        metadata = run_data["metadata"]
        agent_model = metadata.get("agent_model", "unknown")
        model_short = agent_model.split(":")[-1].replace("claude-", "").replace("-", " ").title()
        run_labels.append(model_short)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Agent Evaluation Comparison</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f7fa;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .header h1 {{ margin: 0 0 10px 0; }}
        .header .subtitle {{ opacity: 0.9; }}

        .comparison-grid {{
            display: grid;
            grid-template-columns: repeat({len(runs_data)}, 1fr);
            gap: 20px;
            margin: 20px 0;
        }}

        .run-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        }}
        .run-card h2 {{
            margin: 0 0 15px 0;
            color: #2d3748;
            font-size: 20px;
        }}
        .run-info {{
            font-size: 13px;
            color: #718096;
            margin-bottom: 15px;
        }}

        .stat {{
            margin: 10px 0;
            padding: 10px;
            background: #f7fafc;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
        }}
        .stat-label {{ color: #718096; font-weight: 500; }}
        .stat-value {{ color: #2d3748; font-weight: 600; }}

        .pass-rate {{ font-size: 32px; font-weight: bold; margin: 20px 0; }}
        .pass-rate.high {{ color: #48bb78; }}
        .pass-rate.medium {{ color: #ed8936; }}
        .pass-rate.low {{ color: #f56565; }}

        .section-title {{
            font-size: 24px;
            font-weight: 600;
            margin: 40px 0 20px 0;
            color: #2d3748;
        }}

        table {{
            width: 100%;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.08);
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }}
        th {{
            background: #f7fafc;
            color: #2d3748;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
        }}

        .status-passed {{ color: #48bb78; font-weight: 600; }}
        .status-failed {{ color: #f56565; font-weight: 600; }}

        .score-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 600;
        }}
        .score-high {{ background: #c6f6d5; color: #22543d; }}
        .score-medium {{ background: #feebc8; color: #744210; }}
        .score-low {{ background: #fed7d7; color: #742a2a; }}
        .score-none {{ background: #e2e8f0; color: #718096; }}

        .diff-highlight {{
            background: #fef5e7;
            border-left: 3px solid #f39c12;
        }}

        .toggle-btn {{
            background: #4299e1;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            margin: 20px 0;
        }}
        .toggle-btn:hover {{ background: #3182ce; }}

        .hidden {{ display: none; }}

        .winner {{
            position: relative;
        }}
        .winner::after {{
            content: "🏆";
            position: absolute;
            right: 10px;
            font-size: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔄 Agent Evaluation Comparison</h1>
        <div class="subtitle">Comparing {len(runs_data)} test runs: {", ".join(run_labels)}</div>
    </div>

    <div class="comparison-grid">"""

    # Generate run cards
    for i, (run_data, stats, label) in enumerate(zip(runs_data, runs_stats, run_labels)):
        metadata = run_data["metadata"]

        # Determine pass rate class
        pass_rate = stats["pass_rate"]
        if pass_rate >= 0.8:
            rate_class = "high"
        elif pass_rate >= 0.6:
            rate_class = "medium"
        else:
            rate_class = "low"

        # Check if this run has the best pass rate
        best_pass_rate = max(s["pass_rate"] for s in runs_stats)
        is_winner = stats["pass_rate"] == best_pass_rate and best_pass_rate > 0
        winner_class = " winner" if is_winner else ""

        html += f"""
        <div class="run-card{winner_class}">
            <h2>{label}</h2>
            <div class="run-info">
                Run ID: {run_data['run_id']}<br>
                Model: {metadata.get('agent_model', 'unknown')}<br>
                Date: {metadata.get('timestamp_str', 'unknown')}
            </div>

            <div class="pass-rate {rate_class}">{pass_rate:.1%}</div>

            <div class="stat">
                <span class="stat-label">Tests</span>
                <span class="stat-value">{stats['total_tests']}</span>
            </div>
            <div class="stat">
                <span class="stat-label">Passed</span>
                <span class="stat-value">{stats['passed']}</span>
            </div>
            <div class="stat">
                <span class="stat-label">Failed</span>
                <span class="stat-value">{stats['failed']}</span>
            </div>
            <div class="stat">
                <span class="stat-label">Total Cost</span>
                <span class="stat-value">${stats['total_cost']:.4f}</span>
            </div>
            <div class="stat">
                <span class="stat-label">Avg Cost/Test</span>
                <span class="stat-value">${stats['avg_cost']:.4f}</span>
            </div>"""

        if stats['avg_quality_score'] is not None:
            html += f"""
            <div class="stat">
                <span class="stat-label">Avg Quality</span>
                <span class="stat-value">{stats['avg_quality_score']:.3f}</span>
            </div>"""

        html += """
        </div>"""

    html += """
    </div>

    <h2 class="section-title">Test-by-Test Comparison</h2>

    <button class="toggle-btn" onclick="toggleDiffOnly()">
        <span id="toggle-text">Show Different Results Only</span>
    </button>

    <table id="comparison-table">
        <thead>
            <tr>
                <th>Test Name</th>"""

    # Column headers for each run
    for label in run_labels:
        html += f"""
                <th>{label}</th>"""

    html += """
            </tr>
        </thead>
        <tbody>"""

    # Generate test comparison rows
    for test_name in sorted(common_tests):
        # Get test data from each run
        tests = [get_test_by_name(run["all_tests"], test_name) for run in runs_data]

        # Check if results differ
        statuses = [t.get("status") if t else None for t in tests]
        all_same = len(set(statuses)) == 1

        # Check if scores differ (if present)
        scores = [t.get("quality_score") if t else None for t in tests]
        scores_differ = len(set(s for s in scores if s is not None)) > 1 if any(s is not None for s in scores) else False

        differs = not all_same or scores_differ
        diff_class = " diff-highlight" if differs else ""
        data_diff = "true" if differs else "false"

        html += f"""
            <tr class="test-row{diff_class}" data-differs="{data_diff}">
                <td><strong>{test_name}</strong></td>"""

        # Add columns for each run's result
        for test in tests:
            if not test:
                html += '<td>-</td>'
                continue

            status = test.get("status", "UNKNOWN")
            status_class = "passed" if status == "PASSED" else "failed"

            # Get score if available
            score_html = ""
            if "quality_score" in test:
                score = test["quality_score"]
                if score >= 0.7:
                    score_class = "score-high"
                elif score >= 0.5:
                    score_class = "score-medium"
                else:
                    score_class = "score-low"
                score_html = f'<span class="score-badge {score_class}">{score:.2f}</span><br>'

            cost = test.get("cost", 0.0)
            duration = test.get("duration_ms", 0)

            html += f"""
                <td>
                    {score_html}
                    <span class="status-{status_class}">{status}</span><br>
                    <small>${cost:.4f} | {duration:,}ms</small>
                </td>"""

        html += """
            </tr>"""

    html += """
        </tbody>
    </table>

    <script>
        let showingDiffOnly = false;

        function toggleDiffOnly() {
            const rows = document.querySelectorAll('.test-row');
            const btn = document.getElementById('toggle-text');

            showingDiffOnly = !showingDiffOnly;

            rows.forEach(row => {
                const differs = row.getAttribute('data-differs') === 'true';
                if (showingDiffOnly && !differs) {
                    row.style.display = 'none';
                } else {
                    row.style.display = 'table-row';
                }
            });

            btn.textContent = showingDiffOnly
                ? 'Show All Tests'
                : 'Show Different Results Only';
        }
    </script>
</body>
</html>
"""

    return html


def main():
    """Generate comparison dashboard."""
    parser = argparse.ArgumentParser(
        description="Generate comparison dashboard for agent evaluation runs"
    )
    parser.add_argument(
        "run_ids",
        nargs="+",
        help="Run IDs to compare (2-4 runs)",
    )
    parser.add_argument(
        "--output",
        help="Output file path (defaults to database/agent_eval_reports/dashboards/comparison_<runs>.html)",
    )
    args = parser.parse_args()

    if len(args.run_ids) < 2:
        print("Error: Need at least 2 runs to compare", file=sys.stderr)
        sys.exit(1)

    if len(args.run_ids) > 4:
        print("Error: Maximum 4 runs can be compared at once", file=sys.stderr)
        sys.exit(1)

    base_dir = Path("database/agent_eval_reports")

    if not base_dir.exists():
        print(f"Error: {base_dir} directory not found", file=sys.stderr)
        sys.exit(1)

    # Load data for all runs
    print(f"Loading data for {len(args.run_ids)} runs...")
    runs_data = []
    for run_id in args.run_ids:
        try:
            run_data = load_run_data(base_dir, run_id)
            runs_data.append(run_data)
            print(f"  ✓ Loaded {run_id}")
        except Exception as e:
            print(f"  ✗ Failed to load {run_id}: {e}", file=sys.stderr)
            sys.exit(1)

    # Generate HTML
    print("Generating comparison dashboard...")
    html = generate_comparison_html(runs_data)

    # Determine output file
    if args.output:
        output_file = Path(args.output)
    else:
        dashboards_dir = base_dir / "dashboards"
        dashboards_dir.mkdir(exist_ok=True)

        # Create filename from run IDs
        run_labels = []
        for run_data in runs_data:
            model = run_data["metadata"].get("agent_model", "unknown")
            model_short = model.split(":")[-1].replace("claude-", "").replace("-", "")
            run_labels.append(model_short)

        filename = f"comparison_{'_vs_'.join(run_labels)}.html"
        output_file = dashboards_dir / filename

    # Write file
    with open(output_file, "w") as f:
        f.write(html)

    print(f"\n✅ Comparison dashboard generated: {output_file}")
    print(f"   Comparing: {', '.join(args.run_ids)}")
    print(f"   Total runs: {len(runs_data)}")


if __name__ == "__main__":
    main()
