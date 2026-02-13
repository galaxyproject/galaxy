#!/usr/bin/env python
"""Generate index dashboard for all agent evaluation runs.

Creates a central hub for:
- Browsing all test runs
- Viewing run summaries and metadata
- Launching individual dashboards
- Building comparisons between runs
- Filtering and sorting runs
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_all_runs(base_dir: Path) -> list[dict[str, Any]]:
    """Load metadata and summary for all runs."""
    runs_dir = base_dir / "runs"

    if not runs_dir.exists():
        return []

    all_runs = []

    for run_dir in runs_dir.iterdir():
        if not run_dir.is_dir():
            continue

        run_id = run_dir.name

        # Load metadata
        metadata_file = run_dir / "metadata.json"
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)

        # Load summary if it exists
        summary_file = run_dir / "summary.json"
        summary = {}
        if summary_file.exists():
            with open(summary_file) as f:
                summary = json.load(f)

        # If no summary, calculate basic stats from test files
        if not summary:
            total = 0
            passed = 0
            total_cost = 0.0

            for category_dir in run_dir.iterdir():
                if not category_dir.is_dir():
                    continue
                for test_file in category_dir.glob("*.json"):
                    with open(test_file) as f:
                        test = json.load(f)
                        total += 1
                        if test.get("status") == "PASSED":
                            passed += 1
                        total_cost += test.get("cost", 0.0)

            summary = {
                "totals": {
                    "tests": total,
                    "passed": passed,
                    "failed": total - passed,
                    "pass_rate": passed / total if total > 0 else 0,
                    "total_cost": total_cost,
                }
            }

        all_runs.append({
            "run_id": run_id,
            "metadata": metadata,
            "summary": summary,
        })

    # Sort by timestamp (most recent first)
    all_runs.sort(key=lambda r: r["metadata"].get("timestamp", 0), reverse=True)

    return all_runs


def generate_index_html(all_runs: list[dict[str, Any]]) -> str:
    """Generate HTML index dashboard."""

    html = """<!DOCTYPE html>
<html>
<head>
    <title>Agent Evaluation Dashboard - Index</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f7fa;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .header h1 { margin: 0 0 10px 0; font-size: 32px; }
        .header .subtitle { opacity: 0.9; }

        .controls {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        }

        .filter-section {
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }

        .filter-input {
            padding: 10px 15px;
            border: 1px solid #e2e8f0;
            border-radius: 5px;
            font-size: 14px;
            flex: 1;
            min-width: 200px;
        }

        .filter-select {
            padding: 10px 15px;
            border: 1px solid #e2e8f0;
            border-radius: 5px;
            font-size: 14px;
            background: white;
            cursor: pointer;
        }

        .comparison-section {
            background: #fef5e7;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #f39c12;
            margin-top: 15px;
        }

        .comparison-section h3 {
            margin: 0 0 10px 0;
            color: #744210;
            font-size: 16px;
        }

        .selected-runs {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin: 10px 0;
        }

        .selected-run-tag {
            background: white;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 13px;
            color: #744210;
            border: 1px solid #f39c12;
        }

        .btn {
            background: #4299e1;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: background 0.2s;
        }
        .btn:hover { background: #3182ce; }
        .btn:disabled {
            background: #cbd5e0;
            cursor: not-allowed;
        }

        .btn-danger {
            background: #f56565;
        }
        .btn-danger:hover { background: #e53e3e; }

        .runs-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }

        .run-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.08);
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
            position: relative;
        }
        .run-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.12);
        }
        .run-card.selected {
            border: 2px solid #4299e1;
            box-shadow: 0 4px 12px rgba(66, 153, 225, 0.3);
        }

        .run-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 15px;
        }

        .run-title {
            font-size: 18px;
            font-weight: 600;
            color: #2d3748;
            margin: 0;
        }

        .select-checkbox {
            width: 20px;
            height: 20px;
            cursor: pointer;
        }

        .run-model {
            color: #667eea;
            font-size: 14px;
            font-weight: 500;
            margin: 5px 0;
        }

        .run-date {
            color: #718096;
            font-size: 13px;
            margin: 5px 0;
        }

        .run-stats {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin: 15px 0;
        }

        .stat-item {
            background: #f7fafc;
            padding: 10px;
            border-radius: 5px;
        }

        .stat-label {
            font-size: 11px;
            color: #718096;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .stat-value {
            font-size: 18px;
            font-weight: 600;
            color: #2d3748;
            margin-top: 5px;
        }

        .pass-rate {
            font-size: 24px;
            font-weight: bold;
            margin: 10px 0;
        }
        .pass-rate.high { color: #48bb78; }
        .pass-rate.medium { color: #ed8936; }
        .pass-rate.low { color: #f56565; }

        .run-actions {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }

        .run-link {
            flex: 1;
            text-align: center;
            padding: 8px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-size: 13px;
            font-weight: 500;
            transition: background 0.2s;
        }
        .run-link:hover { background: #5a67d8; }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #718096;
        }
        .empty-state-icon { font-size: 48px; margin-bottom: 20px; }

        .filter-info {
            background: #e6fffa;
            border-left: 4px solid #38b2ac;
            padding: 12px;
            margin-bottom: 20px;
            border-radius: 5px;
            color: #234e52;
            font-size: 14px;
        }

        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Agent Evaluation Dashboard</h1>
        <div class="subtitle">Browse and compare all test runs</div>
    </div>

    <div class="controls">
        <div class="filter-section">
            <input
                type="text"
                id="search-input"
                class="filter-input"
                placeholder="Search by run ID or model..."
                onkeyup="filterRuns()"
            >

            <select id="model-filter" class="filter-select" onchange="filterRuns()">
                <option value="">All Models</option>
                <option value="haiku">Haiku</option>
                <option value="sonnet">Sonnet</option>
                <option value="opus">Opus</option>
            </select>

            <select id="sort-select" class="filter-select" onchange="sortRuns()">
                <option value="date-desc">Newest First</option>
                <option value="date-asc">Oldest First</option>
                <option value="pass-rate-desc">Pass Rate (High to Low)</option>
                <option value="pass-rate-asc">Pass Rate (Low to High)</option>
                <option value="cost-desc">Cost (High to Low)</option>
                <option value="cost-asc">Cost (Low to High)</option>
            </select>
        </div>

        <div class="comparison-section">
            <h3>🔄 Comparison Builder</h3>
            <div id="selected-count">Select 2-4 runs to compare</div>
            <div class="selected-runs" id="selected-runs"></div>
            <button
                id="compare-btn"
                class="btn"
                onclick="buildComparison()"
                disabled
            >
                Generate Comparison
            </button>
            <button
                id="clear-btn"
                class="btn btn-danger"
                onclick="clearSelection()"
                style="margin-left: 10px;"
                disabled
            >
                Clear Selection
            </button>
        </div>
    </div>

    <div id="filter-info" class="filter-info hidden">
        Showing <span id="visible-count">0</span> of <span id="total-count">0</span> runs
    </div>

    <div class="runs-grid" id="runs-grid">"""

    if not all_runs:
        html += """
        <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <h2>No Test Runs Found</h2>
            <p>Run 'make agent-eval' to generate your first test run.</p>
        </div>"""
    else:
        for run in all_runs:
            run_id = run["run_id"]
            metadata = run["metadata"]
            totals = run["summary"].get("totals", {})

            # Extract info
            agent_model = metadata.get("agent_model", "unknown")
            model_display = agent_model.split(":")[-1].replace("claude-", "").replace("-", " ").title()
            date_str = metadata.get("timestamp_str", "Unknown date")

            # Stats
            total_tests = totals.get("tests", 0)
            passed = totals.get("passed", 0)
            failed = totals.get("failed", 0)
            pass_rate = totals.get("pass_rate", 0)
            total_cost = totals.get("total_cost", 0.0)

            # Pass rate class
            if pass_rate >= 0.8:
                rate_class = "high"
            elif pass_rate >= 0.6:
                rate_class = "medium"
            else:
                rate_class = "low"

            # Data attributes for filtering/sorting
            data_attrs = f'data-run-id="{run_id}" data-model="{agent_model}" data-timestamp="{metadata.get("timestamp", 0)}" data-pass-rate="{pass_rate}" data-cost="{total_cost}"'

            html += f"""
        <div class="run-card" {data_attrs}>
            <div class="run-header">
                <div>
                    <h3 class="run-title">{run_id}</h3>
                    <div class="run-model">{model_display}</div>
                    <div class="run-date">📅 {date_str}</div>
                </div>
                <input
                    type="checkbox"
                    class="select-checkbox"
                    data-run-id="{run_id}"
                    onchange="toggleSelection(this)"
                >
            </div>

            <div class="pass-rate {rate_class}">{pass_rate:.1%} Pass Rate</div>

            <div class="run-stats">
                <div class="stat-item">
                    <div class="stat-label">Tests</div>
                    <div class="stat-value">{total_tests}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Passed</div>
                    <div class="stat-value">{passed}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Failed</div>
                    <div class="stat-value">{failed}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Cost</div>
                    <div class="stat-value">${total_cost:.4f}</div>
                </div>
            </div>

            <div class="run-actions">
                <a href="{run_id}.html" class="run-link">View Dashboard</a>
            </div>
        </div>"""

    html += """
    </div>

    <script>
        let selectedRuns = new Set();

        function updateSelectionUI() {
            const count = selectedRuns.size;
            const countDiv = document.getElementById('selected-count');
            const compareBtn = document.getElementById('compare-btn');
            const clearBtn = document.getElementById('clear-btn');
            const selectedRunsDiv = document.getElementById('selected-runs');

            if (count === 0) {
                countDiv.textContent = 'Select 2-4 runs to compare';
                compareBtn.disabled = true;
                clearBtn.disabled = true;
                selectedRunsDiv.innerHTML = '';
            } else if (count === 1) {
                countDiv.textContent = `${count} run selected (select at least 1 more)`;
                compareBtn.disabled = true;
                clearBtn.disabled = false;
            } else if (count <= 4) {
                countDiv.textContent = `${count} runs selected`;
                compareBtn.disabled = false;
                clearBtn.disabled = false;
            } else {
                countDiv.textContent = `${count} runs selected (max 4)`;
                compareBtn.disabled = true;
                clearBtn.disabled = false;
            }

            // Update selected runs display
            selectedRunsDiv.innerHTML = '';
            selectedRuns.forEach(runId => {
                const tag = document.createElement('div');
                tag.className = 'selected-run-tag';
                tag.textContent = runId;
                selectedRunsDiv.appendChild(tag);
            });

            // Update card visual states
            document.querySelectorAll('.run-card').forEach(card => {
                const checkbox = card.querySelector('.select-checkbox');
                if (checkbox && selectedRuns.has(checkbox.dataset.runId)) {
                    card.classList.add('selected');
                } else {
                    card.classList.remove('selected');
                }
            });
        }

        function toggleSelection(checkbox) {
            const runId = checkbox.dataset.runId;

            if (checkbox.checked) {
                if (selectedRuns.size >= 4) {
                    checkbox.checked = false;
                    alert('Maximum 4 runs can be compared at once');
                    return;
                }
                selectedRuns.add(runId);
            } else {
                selectedRuns.delete(runId);
            }

            updateSelectionUI();
        }

        function clearSelection() {
            selectedRuns.clear();
            document.querySelectorAll('.select-checkbox').forEach(cb => {
                cb.checked = false;
            });
            updateSelectionUI();
        }

        function buildComparison() {
            if (selectedRuns.size < 2 || selectedRuns.size > 4) {
                alert('Please select 2-4 runs to compare');
                return;
            }

            const runs = Array.from(selectedRuns);

            // Get model short names for filename
            const labels = runs.map(runId => {
                const card = document.querySelector(`[data-run-id="${runId}"]`);
                const model = card.dataset.model;
                return model.split(':').pop().replace('claude-', '').replace(/-/g, '');
            });

            const filename = `comparison_${labels.join('_vs_')}.html`;

            alert(`Comparison dashboard would be generated at:\\n\\ndatabase/agent_eval_reports/dashboards/${filename}\\n\\nRun this command to generate it:\\n\\npython scripts/generate_comparison_dashboard.py ${runs.join(' ')}`);
        }

        function filterRuns() {
            const searchTerm = document.getElementById('search-input').value.toLowerCase();
            const modelFilter = document.getElementById('model-filter').value.toLowerCase();

            const cards = document.querySelectorAll('.run-card');
            let visibleCount = 0;

            cards.forEach(card => {
                const runId = card.dataset.runId.toLowerCase();
                const model = card.dataset.model.toLowerCase();

                const matchesSearch = !searchTerm || runId.includes(searchTerm) || model.includes(searchTerm);
                const matchesModel = !modelFilter || model.includes(modelFilter);

                if (matchesSearch && matchesModel) {
                    card.style.display = 'block';
                    visibleCount++;
                } else {
                    card.style.display = 'none';
                }
            });

            const totalCount = cards.length;
            document.getElementById('visible-count').textContent = visibleCount;
            document.getElementById('total-count').textContent = totalCount;

            const filterInfo = document.getElementById('filter-info');
            if (visibleCount < totalCount) {
                filterInfo.classList.remove('hidden');
            } else {
                filterInfo.classList.add('hidden');
            }
        }

        function sortRuns() {
            const sortBy = document.getElementById('sort-select').value;
            const grid = document.getElementById('runs-grid');
            const cards = Array.from(document.querySelectorAll('.run-card'));

            cards.sort((a, b) => {
                switch(sortBy) {
                    case 'date-desc':
                        return parseFloat(b.dataset.timestamp) - parseFloat(a.dataset.timestamp);
                    case 'date-asc':
                        return parseFloat(a.dataset.timestamp) - parseFloat(b.dataset.timestamp);
                    case 'pass-rate-desc':
                        return parseFloat(b.dataset.passRate) - parseFloat(a.dataset.passRate);
                    case 'pass-rate-asc':
                        return parseFloat(a.dataset.passRate) - parseFloat(b.dataset.passRate);
                    case 'cost-desc':
                        return parseFloat(b.dataset.cost) - parseFloat(a.dataset.cost);
                    case 'cost-asc':
                        return parseFloat(a.dataset.cost) - parseFloat(b.dataset.cost);
                    default:
                        return 0;
                }
            });

            // Re-append in sorted order
            cards.forEach(card => grid.appendChild(card));
        }

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            const totalCount = document.querySelectorAll('.run-card').length;
            document.getElementById('total-count').textContent = totalCount;
            updateSelectionUI();
        });
    </script>
</body>
</html>
"""

    return html


def main():
    """Generate index dashboard."""
    parser = argparse.ArgumentParser(description="Generate index dashboard for all runs")
    parser.add_argument(
        "--output",
        help="Output file path (defaults to database/agent_eval_reports/dashboards/index.html)",
    )
    args = parser.parse_args()

    base_dir = Path("database/agent_eval_reports")

    if not base_dir.exists():
        print(f"Error: {base_dir} directory not found", file=sys.stderr)
        print("Run 'make agent-eval' first to generate test reports", file=sys.stderr)
        sys.exit(1)

    # Load all runs
    print("Loading all test runs...")
    all_runs = load_all_runs(base_dir)
    print(f"Found {len(all_runs)} runs")

    # Generate HTML
    print("Generating index dashboard...")
    html = generate_index_html(all_runs)

    # Determine output file
    if args.output:
        output_file = Path(args.output)
    else:
        dashboards_dir = base_dir / "dashboards"
        dashboards_dir.mkdir(exist_ok=True)
        output_file = dashboards_dir / "index.html"

    # Write file
    with open(output_file, "w") as f:
        f.write(html)

    print(f"\n✅ Index dashboard generated: {output_file}")
    print(f"   Total runs: {len(all_runs)}")
    if all_runs:
        print(f"   Latest run: {all_runs[0]['run_id']}")


if __name__ == "__main__":
    main()
