#!/usr/bin/env python
"""Generate interactive HTML dashboard from agent evaluation test reports.

Reads versioned agent evaluation reports from database/agent_eval_reports/runs/ and creates
an interactive dashboard with:
- Auto-discovered category tabs (bioinformatics, routing, tool_recommendations, etc.)
- Agent and judge model information
- Quality scores with color coding
- 3-level progressive disclosure (summary → overview → deep dive)
- Agent/Judge visual separation
- Sortable columns
- Expandable details (all collapsed by default)
"""
import argparse
import html
import json
import sys
import time
from pathlib import Path
from typing import Any


def find_latest_run(base_dir: Path) -> Path | None:
    """Find the most recent run directory by timestamp."""
    runs_dir = base_dir / "runs"
    if not runs_dir.exists():
        return None

    # Get all run directories sorted by modification time (most recent first)
    run_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
    if not run_dirs:
        return None

    # Sort by directory name (which includes timestamp) in descending order
    run_dirs.sort(reverse=True)
    return run_dirs[0]


def load_run_metadata(run_dir: Path) -> dict[str, Any]:
    """Load metadata.json for this run."""
    metadata_file = run_dir / "metadata.json"
    if not metadata_file.exists():
        return {}

    with open(metadata_file) as f:
        return json.load(f)


def load_test_results(run_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Auto-discover all categories and load test reports.

    Returns:
        Dict mapping category names to lists of test reports
    """
    results = {}

    # Scan all subdirectories (each is a category)
    for category_dir in run_dir.iterdir():
        if not category_dir.is_dir():
            continue

        category_name = category_dir.name

        # Skip non-category files
        if category_name in ["metadata.json", "summary.json"]:
            continue

        category_tests = []
        for test_file in category_dir.glob("*.json"):
            with open(test_file) as f:
                category_tests.append(json.load(f))

        if category_tests:
            results[category_name] = category_tests

    return results


def generate_summary_stats(all_tests: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate summary statistics across all tests."""
    total = len(all_tests)
    passed = sum(1 for t in all_tests if t.get("status") == "PASSED")
    failed = total - passed

    # Calculate totals
    total_cost = sum(t.get("cost", 0.0) for t in all_tests)
    total_duration = sum(t.get("duration_ms", 0) for t in all_tests)

    # Calculate average quality score (if present)
    quality_scores = [t["quality_score"] for t in all_tests if "quality_score" in t]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / total if total > 0 else 0,
        "total_cost": total_cost,
        "total_duration_ms": total_duration,
        "avg_quality_score": avg_quality
    }


def format_category_name(category: str) -> str:
    """Convert category slug to display name."""
    return category.replace('_', ' ').title()


def get_score_class(score: float) -> str:
    """Get CSS class for quality score badge."""
    if score >= 0.7:
        return "score-high"
    elif score >= 0.5:
        return "score-medium"
    else:
        return "score-low"


def generate_html(run_dir: Path, metadata: dict[str, Any], results_by_category: dict[str, list]) -> str:
    """Generate HTML dashboard."""

    # Flatten all tests for overall stats
    all_tests = []
    for tests in results_by_category.values():
        all_tests.extend(tests)

    stats = generate_summary_stats(all_tests)

    # Extract metadata
    run_id = metadata.get("run_id", "unknown")
    agent_model = metadata.get("agent_model", "unknown")
    judge_model = metadata.get("judge_model", "unknown")
    timestamp_str = metadata.get("timestamp_str", time.strftime("%Y-%m-%d %H:%M:%S"))

    # Start HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Agent Eval Dashboard - {run_id}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f7fa;
        }}

        /* Header */
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{ margin: 0 0 10px 0; font-size: 32px; }}
        .header .subtitle {{ opacity: 0.9; margin: 5px 0; }}
        .header .run-info {{
            display: flex;
            gap: 30px;
            margin-top: 15px;
            font-size: 14px;
            opacity: 0.95;
        }}
        .header .run-info-item {{ display: flex; align-items: center; gap: 8px; }}
        .header .run-info-label {{ opacity: 0.8; }}

        /* Summary Stats */
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        }}
        .stat h3 {{ margin: 0 0 10px 0; color: #718096; font-size: 14px; font-weight: 500; }}
        .stat .value {{ font-size: 36px; font-weight: bold; color: #2d3748; }}
        .stat .subvalue {{ font-size: 14px; color: #718096; margin-top: 5px; }}
        .passed {{ color: #48bb78; }}
        .failed {{ color: #f56565; }}

        /* Category Tabs */
        .tabs {{
            display: flex;
            gap: 10px;
            margin: 30px 0 20px 0;
            border-bottom: 2px solid #e2e8f0;
            overflow-x: auto;
        }}
        .tab-button {{
            background: none;
            border: none;
            padding: 12px 20px;
            cursor: pointer;
            font-size: 15px;
            font-weight: 500;
            color: #718096;
            border-bottom: 3px solid transparent;
            transition: all 0.2s;
            white-space: nowrap;
        }}
        .tab-button:hover {{ color: #4a5568; background: #f7fafc; }}
        .tab-button.active {{
            color: #667eea;
            border-bottom-color: #667eea;
        }}

        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}

        /* Table */
        .table-container {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.08);
            overflow: hidden;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 14px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }}
        th {{
            background: #f7fafc;
            color: #2d3748;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            cursor: pointer;
            user-select: none;
        }}
        th:hover {{ background: #edf2f7; }}
        tbody tr {{ cursor: pointer; }}
        tbody tr:hover td {{ background: #f7fafc; }}

        /* Status & Score Badges */
        .status-badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        .status-passed {{ background: #c6f6d5; color: #22543d; }}
        .status-failed {{ background: #fed7d7; color: #742a2a; }}

        .score-badge {{
            display: inline-block;
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 700;
        }}
        .score-high {{ background: #c6f6d5; color: #22543d; }}
        .score-medium {{ background: #feebc8; color: #744210; }}
        .score-low {{ background: #fed7d7; color: #742a2a; }}

        /* Expandable Details */
        .expand-btn {{
            background: #667eea;
            color: white;
            border: none;
            padding: 6px 14px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: background 0.2s;
        }}
        .expand-btn:hover {{ background: #5a67d8; }}

        .details-row {{ display: none; }}
        .details-row.show {{ display: table-row; }}

        .details-container {{
            padding: 20px;
            background: #f7fafc;
            border-top: 3px solid #e2e8f0;
        }}

        /* Two-Column Layout for Agent/Judge */
        .two-column-layout {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 20px 0;
        }}

        /* Agent Section (Blue) */
        .agent-section {{
            background: #ebf8ff;
            border-left: 4px solid #4299e1;
            padding: 20px;
            border-radius: 6px;
        }}
        .agent-section h3 {{
            margin: 0 0 15px 0;
            color: #2c5282;
            font-size: 16px;
        }}

        /* Judge Section (Yellow) */
        .judge-section {{
            background: #fefcbf;
            border-left: 4px solid #ecc94b;
            padding: 20px;
            border-radius: 6px;
        }}
        .judge-section h3 {{
            margin: 0 0 15px 0;
            color: #744210;
            font-size: 16px;
        }}

        /* Metrics Grid */
        .metrics-grid {{
            display: grid;
            gap: 10px;
            margin-bottom: 15px;
        }}
        .metric {{
            display: flex;
            justify-content: space-between;
            padding: 8px;
            background: white;
            border-radius: 4px;
            font-size: 14px;
        }}
        .metric label {{
            color: #718096;
            font-weight: 500;
        }}
        .metric span {{
            color: #2d3748;
            font-weight: 600;
        }}

        /* Toggle Buttons */
        .toggle-btn {{
            background: #4299e1;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 13px;
            margin: 10px 0;
            transition: background 0.2s;
        }}
        .toggle-btn:hover {{ background: #3182ce; }}

        .judge-toggle-btn {{
            background: #ecc94b;
            color: #744210;
        }}
        .judge-toggle-btn:hover {{ background: #d69e2e; }}

        .secondary-toggle {{
            background: #a0aec0;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            margin-top: 10px;
        }}
        .secondary-toggle:hover {{ background: #718096; }}

        /* Collapsible Content */
        .collapsible-content {{
            display: none;
            margin-top: 15px;
            padding: 15px;
            background: white;
            border-radius: 5px;
            border: 1px solid #e2e8f0;
        }}
        .collapsible-content.show {{ display: block; }}

        /* Prompt Section */
        .prompt-section {{
            margin: 20px 0;
            padding: 15px;
            background: white;
            border-radius: 6px;
            border-left: 4px solid #9f7aea;
        }}
        .prompt-section h3 {{
            margin: 0 0 10px 0;
            color: #553c9a;
            font-size: 16px;
        }}
        .prompt-text {{
            color: #2d3748;
            line-height: 1.6;
            font-size: 14px;
        }}

        /* Response/Reasoning Text */
        .response-text, .reasoning-text {{
            color: #2d3748;
            line-height: 1.7;
            padding: 15px;
            background: #f7fafc;
            border-radius: 5px;
            white-space: pre-wrap;
            font-size: 14px;
        }}

        /* Pre/Code */
        pre {{
            background: #2d3748;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 13px;
            line-height: 1.5;
        }}

        /* Utilities */
        .no-data {{
            padding: 40px;
            text-align: center;
            color: #718096;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Agent Evaluation Dashboard</h1>
        <div class="subtitle">Run: {run_id}</div>
        <div class="run-info">
            <div class="run-info-item">
                <span class="run-info-label">Agent Model:</span>
                <strong>{agent_model}</strong>
            </div>
            <div class="run-info-item">
                <span class="run-info-label">Judge Model:</span>
                <strong>{judge_model}</strong>
            </div>
            <div class="run-info-item">
                <span class="run-info-label">Date:</span>
                <strong>{timestamp_str}</strong>
            </div>
        </div>
    </div>

    <div class="stats">
        <div class="stat">
            <h3>Total Tests</h3>
            <div class="value">{stats['total']}</div>
        </div>
        <div class="stat">
            <h3>Passed</h3>
            <div class="value passed">{stats['passed']}</div>
            <div class="subvalue">{stats['pass_rate']:.1%} pass rate</div>
        </div>
        <div class="stat">
            <h3>Failed</h3>
            <div class="value failed">{stats['failed']}</div>
        </div>
        <div class="stat">
            <h3>Total Cost</h3>
            <div class="value">${stats['total_cost']:.4f}</div>
        </div>"""

    # Add average quality score if available
    if stats['avg_quality_score'] is not None:
        html += f"""
        <div class="stat">
            <h3>Avg Quality Score</h3>
            <div class="value">{stats['avg_quality_score']:.3f}</div>
        </div>"""

    html += """
    </div>

    <div class="tabs">"""

    # Generate category tabs
    for i, (category, tests) in enumerate(results_by_category.items()):
        active_class = " active" if i == 0 else ""
        display_name = format_category_name(category)
        html += f"""
        <button class="tab-button{active_class}" onclick="switchTab('{category}')">
            {display_name} ({len(tests)})
        </button>"""

    html += """
    </div>
"""

    # Generate category content
    for i, (category, tests) in enumerate(results_by_category.items()):
        active_class = " active" if i == 0 else ""
        html += f"""
    <div id="tab-{category}" class="tab-content{active_class}">
        <div class="table-container">
            <table>
                <thead>
                    <tr>"""

        # Only show Score column if any test has quality_score
        has_scores = any("quality_score" in t for t in tests)
        if has_scores:
            html += """
                        <th onclick="sortTable('{category}', 0)">Score</th>"""

        html += f"""
                        <th onclick="sortTable('{category}', 1)">Test Name</th>
                        <th onclick="sortTable('{category}', 2)">Status</th>
                        <th onclick="sortTable('{category}', 3)">Duration</th>
                        <th onclick="sortTable('{category}', 4)">Cost</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>"""

        # Generate test rows
        for test in tests:
            test_id = f"{category}-{test.get('test_name', 'unknown').replace('.', '-')}"
            test_name = test.get("test_name", "Unknown")
            status = test.get("status", "UNKNOWN")
            duration_ms = test.get("duration_ms", 0)
            duration_s = duration_ms / 1000.0  # Convert to seconds
            cost = test.get("cost", 0.0)

            status_class = "passed" if status == "PASSED" else "failed"
            badge_class = "status-passed" if status == "PASSED" else "status-failed"

            html += f"""
                    <tr onclick="toggleDetails('{test_id}', event)">"""

            # Score column (if applicable)
            if has_scores:
                if "quality_score" in test:
                    score = test["quality_score"]
                    score_class = get_score_class(score)
                    html += f"""
                        <td><span class="score-badge {score_class}">{score:.2f}</span></td>"""
                else:
                    html += """
                        <td>-</td>"""

            html += f"""
                        <td><strong>{test_name}</strong></td>
                        <td><span class="status-badge {badge_class}">{status}</span></td>
                        <td>{duration_s:.1f}s</td>
                        <td>${cost:.4f}</td>
                        <td>
                            <button class="expand-btn" onclick="event.stopPropagation(); toggleDetails('{test_id}', event)">
                                Expand
                            </button>
                        </td>
                    </tr>"""

            # Details row (collapsed by default)
            html += f"""
                    <tr id="{test_id}-details" class="details-row">
                        <td colspan="{6 if has_scores else 5}">
                            <div class="details-container">
                                {generate_test_details(test, test_id)}
                            </div>
                        </td>
                    </tr>"""

        html += """
                </tbody>
            </table>
        </div>
    </div>
"""

    # Add JavaScript
    html += """
    <script>
        function switchTab(tabName) {
            // Hide all tabs
            const tabs = document.querySelectorAll('.tab-content');
            tabs.forEach(tab => tab.classList.remove('active'));

            // Deactivate all buttons
            const buttons = document.querySelectorAll('.tab-button');
            buttons.forEach(btn => btn.classList.remove('active'));

            // Show selected tab
            document.getElementById('tab-' + tabName).classList.add('active');

            // Activate selected button
            event.target.classList.add('active');
        }

        function toggleDetails(testId, event) {
            const detailsRow = document.getElementById(testId + '-details');
            const row = event.currentTarget;
            const btn = row.querySelector('.expand-btn');

            if (detailsRow.classList.contains('show')) {
                detailsRow.classList.remove('show');
                if (btn) btn.textContent = 'Expand';
            } else {
                detailsRow.classList.add('show');
                if (btn) btn.textContent = 'Collapse';
            }
        }

        function toggleSection(sectionId) {
            const section = document.getElementById(sectionId);
            const btn = event.target;

            if (section.classList.contains('show')) {
                section.classList.remove('show');
                btn.textContent = btn.textContent.replace('Hide', 'Show');
            } else {
                section.classList.add('show');
                btn.textContent = btn.textContent.replace('Show', 'Hide');
            }
        }

        function sortTable(category, colIndex) {
            // Table sorting implementation would go here
            console.log('Sort table', category, 'by column', colIndex);
        }
    </script>
</body>
</html>
"""

    return html


def generate_test_details(test: dict[str, Any], test_id: str) -> str:
    """Generate detailed view for a single test with 3-level progressive disclosure.

    All user-provided content is HTML-escaped to prevent XSS attacks.
    """

    # Extract data and escape for HTML safety
    prompt = html.escape(test.get("prompt", ""))
    agent_response = html.escape(test.get("agent_response", ""))

    # Agent metrics
    agent_tokens = test.get("detailed_metrics", {}).get("agent_tokens", {})
    agent_tokens_in = agent_tokens.get("input", 0)
    agent_tokens_out = agent_tokens.get("output", 0)
    agent_cost = test.get("detailed_metrics", {}).get("costs", {}).get("agent_cost", 0.0)
    agent_model = test.get("agent_model", "unknown")
    query_duration_ms = test.get("query_duration_ms", 0)
    query_duration_s = query_duration_ms / 1000.0  # Convert to seconds

    # Judge metrics (if present)
    judge_tokens = test.get("detailed_metrics", {}).get("judge_tokens", {})
    judge_tokens_in = judge_tokens.get("input", 0)
    judge_tokens_out = judge_tokens.get("output", 0)
    judge_cost = test.get("detailed_metrics", {}).get("costs", {}).get("judge_cost", 0.0)
    judge_model = test.get("judge_model", "unknown")
    quality_score = test.get("quality_score")
    judge_reasoning = html.escape(test.get("judge_reasoning", ""))
    rubric = html.escape(test.get("rubric", ""))
    min_score = test.get("min_score_threshold", 0.7)

    html = f"""
                                <!-- Level 2: Agent + Judge Overview (Side by Side) -->
                                <div class="two-column-layout">

                                    <!-- Agent Section (Left - Blue) -->
                                    <div class="agent-section">
                                        <h3>Agent Response</h3>
                                        <div class="metrics-grid">
                                            <div class="metric">
                                                <label>Model:</label>
                                                <span>{agent_model}</span>
                                            </div>
                                            <div class="metric">
                                                <label>Tokens:</label>
                                                <span>{agent_tokens_in:,} in / {agent_tokens_out:,} out</span>
                                            </div>
                                            <div class="metric">
                                                <label>Cost:</label>
                                                <span>${agent_cost:.4f}</span>
                                            </div>
                                            <div class="metric">
                                                <label>Duration:</label>
                                                <span>{query_duration_s:.1f}s</span>
                                            </div>
                                        </div>

                                        <button class="toggle-btn" onclick="toggleSection('{test_id}-agent-full')">
                                            Show Full Response
                                        </button>

                                        <!-- Level 3: Full Agent Response -->
                                        <div id="{test_id}-agent-full" class="collapsible-content">
                                            <div class="response-text">{agent_response}</div>
                                        </div>
                                    </div>

                                    <!-- Judge Section (Right - Yellow) -->
                                    <div class="judge-section">
                                        <h3>Judge Evaluation</h3>"""

    # Only show judge info if it exists
    if quality_score is not None:
        score_class = get_score_class(quality_score)
        status_text = "PASSED" if quality_score >= min_score else "FAILED"

        html += f"""
                                        <div class="metrics-grid">
                                            <div class="metric">
                                                <label>Model:</label>
                                                <span>{judge_model}</span>
                                            </div>
                                            <div class="metric">
                                                <label>Score:</label>
                                                <span class="score-badge {score_class}">{quality_score:.2f} / 1.00</span>
                                            </div>
                                            <div class="metric">
                                                <label>Tokens:</label>
                                                <span>{judge_tokens_in:,} in / {judge_tokens_out:,} out</span>
                                            </div>
                                            <div class="metric">
                                                <label>Cost:</label>
                                                <span>${judge_cost:.4f}</span>
                                            </div>
                                            <div class="metric">
                                                <label>Status:</label>
                                                <span>{status_text} (≥{min_score:.2f})</span>
                                            </div>
                                        </div>

                                        <button class="toggle-btn judge-toggle-btn" onclick="toggleSection('{test_id}-judge-reasoning')">
                                            Show Judge Reasoning
                                        </button>

                                        <!-- Level 3: Judge Reasoning -->
                                        <div id="{test_id}-judge-reasoning" class="collapsible-content">
                                            <h4 style="margin: 0 0 10px 0; color: #744210;">Reasoning:</h4>
                                            <div class="reasoning-text">{judge_reasoning}</div>

                                            <h4 style="margin: 20px 0 10px 0; color: #744210;">Rubric:</h4>
                                            <pre>{rubric}</pre>
                                        </div>"""
    else:
        html += """
                                        <p style="color: #718096; font-style: italic;">No judge evaluation available for this test.</p>"""

    html += """
                                    </div>

                                </div>

                                <!-- Prompt (Full Width) -->
                                <div class="prompt-section">
                                    <h3>User Prompt</h3>
                                    <div class="prompt-text">""" + prompt + """</div>
                                </div>

                                <!-- Advanced Details (Raw JSON) -->
                                <button class="secondary-toggle" onclick="toggleSection('""" + test_id + """-advanced')">
                                    Show Raw JSON
                                </button>
                                <div id=\"""" + test_id + """-advanced" class="collapsible-content">
                                    <pre>""" + json.dumps(test, indent=2) + """</pre>
                                </div>
"""

    return html


def generate_index_html(base_dir: Path) -> str:
    """Generate index.html listing all available runs."""
    runs_dir = base_dir / "runs"

    if not runs_dir.exists():
        return generate_empty_index()

    # Collect all run metadata
    runs = []
    for run_dir in sorted(runs_dir.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue

        metadata_file = run_dir / "metadata.json"
        summary_file = run_dir / "summary.json"

        if not metadata_file.exists():
            continue

        with open(metadata_file) as f:
            metadata = json.load(f)

        # Load summary if available
        summary = {}
        if summary_file.exists():
            with open(summary_file) as f:
                summary = json.load(f)

        run_info = {
            "run_id": metadata.get("run_id", run_dir.name),
            "timestamp": metadata.get("timestamp", 0),
            "timestamp_str": metadata.get("timestamp_str", "Unknown"),
            "agent_model": metadata.get("agent_model", "unknown"),
            "judge_model": metadata.get("judge_model", "unknown"),
            "totals": summary.get("totals", {
                "tests": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
                "total_cost": 0.0
            })
        }
        runs.append(run_info)

    # Generate HTML
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

        .filter-info {
            background: #e8f4f8;
            padding: 10px 15px;
            border-radius: 5px;
            margin-top: 10px;
            font-size: 14px;
            color: #2c5282;
        }
        .filter-info.hidden { display: none; }

        .runs-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }

        .run-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.08);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .run-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .run-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }

        .run-title {
            margin: 0 0 5px 0;
            font-size: 16px;
            font-weight: 600;
            color: #2d3748;
            font-family: 'Courier New', monospace;
        }

        .run-model {
            font-size: 13px;
            color: #718096;
            margin-bottom: 3px;
        }

        .run-date {
            font-size: 12px;
            color: #a0aec0;
        }

        .select-checkbox {
            width: 20px;
            height: 20px;
            cursor: pointer;
        }

        .pass-rate {
            padding: 8px 15px;
            border-radius: 5px;
            font-weight: 600;
            margin-bottom: 15px;
            text-align: center;
        }
        .pass-rate.high { background: #c6f6d5; color: #22543d; }
        .pass-rate.medium { background: #fef5e7; color: #744210; }
        .pass-rate.low { background: #fed7d7; color: #742a2a; }

        .run-stats {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin-bottom: 15px;
        }

        .stat-item {
            text-align: center;
        }

        .stat-label {
            font-size: 11px;
            color: #a0aec0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 3px;
        }

        .stat-value {
            font-size: 18px;
            font-weight: 700;
            color: #2d3748;
        }

        .run-actions {
            display: flex;
            gap: 10px;
        }

        .run-link {
            flex: 1;
            background: #4299e1;
            color: white;
            text-align: center;
            padding: 10px;
            border-radius: 5px;
            text-decoration: none;
            font-weight: 500;
            font-size: 14px;
            transition: background 0.2s;
        }
        .run-link:hover { background: #3182ce; }

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
            min-height: 30px;
        }

        .selected-run-tag {
            background: white;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 13px;
            color: #744210;
            border: 1px solid #f39c12;
        }

        .comparison-actions {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #718096;
        }

        .empty-state h2 {
            font-size: 24px;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Agent Evaluation Dashboard</h1>
        <div class="subtitle">Browse and compare test runs</div>
    </div>

    <div class="controls">
        <div class="filter-section">
            <input
                type="text"
                id="search-input"
                class="filter-input"
                placeholder="Search by run ID or model..."
                oninput="filterRuns()"
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

        <div id="filter-info" class="filter-info hidden">
            Showing <span id="visible-count">0</span> of <span id="total-count">0</span> runs
        </div>

        <div class="comparison-section">
            <h3>Build Comparison Dashboard</h3>
            <p style="margin: 0 0 10px 0; font-size: 14px; color: #744210;">
                Select 2-4 runs to compare side-by-side
            </p>
            <div class="selected-runs" id="selected-runs">
                <span style="color: #a0aec0; font-size: 13px;">No runs selected</span>
            </div>
            <div class="comparison-actions">
                <button class="btn" id="build-btn" onclick="buildComparison()" disabled>
                    Build Comparison
                </button>
                <button class="btn" onclick="clearSelection()" style="background: #718096;">
                    Clear Selection
                </button>
            </div>
        </div>
    </div>

    <div class="runs-grid" id="runs-grid">
"""

    # Generate run cards
    for run in runs:
        run_id = run["run_id"]
        timestamp = run["timestamp"]
        timestamp_str = run["timestamp_str"]
        agent_model = run["agent_model"]
        totals = run["totals"]

        # Extract model short name for display
        model_display = agent_model.split(":")[-1].replace("claude-", "").replace("-", " ").title()

        # Calculate pass rate class
        pass_rate = totals.get("pass_rate", 0.0)
        if pass_rate >= 0.8:
            pass_rate_class = "high"
        elif pass_rate >= 0.5:
            pass_rate_class = "medium"
        else:
            pass_rate_class = "low"

        html += f"""
        <div class="run-card" data-run-id="{run_id}" data-model="{agent_model}" data-timestamp="{timestamp}" data-pass-rate="{pass_rate}" data-cost="{totals.get('total_cost', 0.0)}">
            <div class="run-header">
                <div>
                    <h3 class="run-title">{run_id}</h3>
                    <div class="run-model">{model_display}</div>
                    <div class="run-date">{timestamp_str}</div>
                </div>
                <input
                    type="checkbox"
                    class="select-checkbox"
                    data-run-id="{run_id}"
                    onchange="toggleSelection(this)"
                >
            </div>

            <div class="pass-rate {pass_rate_class}">{pass_rate*100:.1f}% Pass Rate</div>

            <div class="run-stats">
                <div class="stat-item">
                    <div class="stat-label">Tests</div>
                    <div class="stat-value">{totals.get('tests', 0)}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Passed</div>
                    <div class="stat-value">{totals.get('passed', 0)}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Failed</div>
                    <div class="stat-value">{totals.get('failed', 0)}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Cost</div>
                    <div class="stat-value">${totals.get('total_cost', 0.0):.4f}</div>
                </div>
            </div>

            <div class="run-actions">
                <a href="{run_id}.html" class="run-link">View Dashboard</a>
            </div>
        </div>
"""

    html += """
    </div>

    <script>
        const selectedRuns = new Set();

        function toggleSelection(checkbox) {
            const runId = checkbox.dataset.runId;
            if (checkbox.checked) {
                selectedRuns.add(runId);
            } else {
                selectedRuns.delete(runId);
            }
            updateSelectionUI();
        }

        function updateSelectionUI() {
            const container = document.getElementById('selected-runs');
            const buildBtn = document.getElementById('build-btn');

            if (selectedRuns.size === 0) {
                container.innerHTML = '<span style="color: #a0aec0; font-size: 13px;">No runs selected</span>';
                buildBtn.disabled = true;
            } else {
                container.innerHTML = '';
                selectedRuns.forEach(runId => {
                    const tag = document.createElement('div');
                    tag.className = 'selected-run-tag';
                    tag.textContent = runId;
                    container.appendChild(tag);
                });
                buildBtn.disabled = selectedRuns.size < 2 || selectedRuns.size > 4;
            }
        }

        function clearSelection() {
            selectedRuns.clear();
            document.querySelectorAll('.select-checkbox').forEach(cb => {
                cb.checked = false;
            });
            updateSelectionUI();
        }

        async function buildComparison() {
            if (selectedRuns.size < 2 || selectedRuns.size > 4) {
                alert('Please select 2-4 runs to compare');
                return;
            }

            const runs = Array.from(selectedRuns);

            // Show loading message
            const buildBtn = document.getElementById('build-btn');
            const originalText = buildBtn.textContent;
            buildBtn.textContent = 'Loading...';
            buildBtn.disabled = true;

            try {
                // Fetch data for each run
                const runData = await Promise.all(runs.map(async runId => {
                    const metadataRes = await fetch(`../runs/${runId}/metadata.json`);
                    const metadata = await metadataRes.json();

                    const summaryRes = await fetch(`../runs/${runId}/summary.json`);
                    const summary = await summaryRes.json();

                    return { runId, metadata, summary };
                }));

                // Generate comparison HTML
                const comparisonHtml = generateComparisonHtml(runData);

                // Save to file (construct filename from run IDs)
                const filename = `comparison_${runs.map(r => r.split('_').pop()).join('_vs_')}.html`;

                // Open in new tab
                const newWindow = window.open('', '_blank');
                newWindow.document.write(comparisonHtml);
                newWindow.document.close();
                newWindow.document.title = 'Agent Evaluation Comparison';

                // Also save to dashboards directory by creating a download
                const blob = new Blob([comparisonHtml], { type: 'text/html' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                a.click();
                URL.revokeObjectURL(url);

            } catch (error) {
                console.error('Error building comparison:', error);
                alert('Error loading comparison data. Make sure all runs have complete data files.');
            } finally {
                buildBtn.textContent = originalText;
                buildBtn.disabled = false;
                updateSelectionUI();
            }
        }

        function generateComparisonHtml(runData) {
            // Generate comprehensive comparison HTML
            const runIds = runData.map(r => r.runId);
            const models = runData.map(r => r.metadata.agent_model.split(':').pop().replace('claude-', ''));

            let html = `<!DOCTYPE html>
<html>
<head>
    <title>Agent Evaluation Comparison</title>
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
        .header .subtitle { opacity: 0.9; font-size: 16px; }
        .comparison-grid {
            display: grid;
            grid-template-columns: repeat(${runData.length}, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }
        .run-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .run-card h3 {
            margin: 0 0 15px 0;
            font-size: 14px;
            color: #667eea;
            font-family: 'Courier New', monospace;
        }
        .metric-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        .metric-label {
            font-size: 13px;
            color: #718096;
            font-weight: 500;
        }
        .metric-value {
            font-size: 14px;
            font-weight: 700;
            color: #2d3748;
        }
        .metric-value.high { color: #22543d; }
        .metric-value.medium { color: #744210; }
        .metric-value.low { color: #742a2a; }
        .section-title {
            font-size: 20px;
            font-weight: 700;
            margin: 30px 0 15px 0;
            color: #2d3748;
        }
        .comparison-table {
            width: 100%;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .comparison-table th, .comparison-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        .comparison-table th {
            background: #f7fafc;
            font-weight: 600;
            font-size: 13px;
            color: #4a5568;
        }
        .comparison-table td {
            font-size: 14px;
        }
        .winner {
            background: #c6f6d5;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Agent Evaluation Comparison</h1>
        <div class="subtitle">Comparing ${runData.length} test runs: ${models.join(' vs ')}</div>
    </div>

    <h2 class="section-title">Overview</h2>
    <div class="comparison-grid">
`;

            // Overview cards for each run
            runData.forEach(({ runId, metadata, summary }) => {
                const totals = summary.totals;
                const passRate = totals.pass_rate * 100;
                const passRateClass = passRate >= 80 ? 'high' : passRate >= 50 ? 'medium' : 'low';

                html += `
        <div class="run-card">
            <h3>${runId}</h3>
            <div class="metric-row">
                <span class="metric-label">Model</span>
                <span class="metric-value">${metadata.agent_model.split(':').pop().replace('claude-', '')}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Tests</span>
                <span class="metric-value">${totals.tests}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Pass Rate</span>
                <span class="metric-value ${passRateClass}">${passRate.toFixed(1)}%</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Avg Score</span>
                <span class="metric-value">${totals.avg_quality_score?.toFixed(2) || 'N/A'}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Total Cost</span>
                <span class="metric-value">$${totals.total_cost.toFixed(4)}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Total Duration</span>
                <span class="metric-value">${(totals.total_duration_ms / 1000).toFixed(1)}s</span>
            </div>
        </div>
`;
            });

            html += `
    </div>

    <h2 class="section-title">Performance Metrics</h2>
    <table class="comparison-table">
        <thead>
            <tr>
                <th>Metric</th>
`;

            runData.forEach(({ runId }) => {
                html += `                <th>${runId.split('_').pop()}</th>\\n`;
            });

            html += `
            </tr>
        </thead>
        <tbody>
`;

            // Find best values for highlighting
            const passRates = runData.map(r => r.summary.totals.pass_rate);
            const avgScores = runData.map(r => r.summary.totals.avg_quality_score || 0);
            const costs = runData.map(r => r.summary.totals.total_cost);

            const bestPassRate = Math.max(...passRates);
            const bestAvgScore = Math.max(...avgScores);
            const lowestCost = Math.min(...costs);

            // Pass Rate row
            html += `            <tr>\\n                <td><strong>Pass Rate</strong></td>\\n`;
            runData.forEach(({ summary }) => {
                const rate = summary.totals.pass_rate;
                const isWinner = rate === bestPassRate;
                html += `                <td class="${isWinner ? 'winner' : ''}">${(rate * 100).toFixed(1)}%</td>\\n`;
            });
            html += `            </tr>\\n`;

            // Avg Quality Score row
            html += `            <tr>\\n                <td><strong>Avg Quality Score</strong></td>\\n`;
            runData.forEach(({ summary }) => {
                const score = summary.totals.avg_quality_score;
                const isWinner = score === bestAvgScore && score > 0;
                html += `                <td class="${isWinner ? 'winner' : ''}">${score?.toFixed(2) || 'N/A'}</td>\\n`;
            });
            html += `            </tr>\\n`;

            // Tests Passed row
            html += `            <tr>\\n                <td><strong>Tests Passed</strong></td>\\n`;
            runData.forEach(({ summary }) => {
                html += `                <td>${summary.totals.passed} / ${summary.totals.tests}</td>\\n`;
            });
            html += `            </tr>\\n`;

            // Total Cost row
            html += `            <tr>\\n                <td><strong>Total Cost</strong></td>\\n`;
            runData.forEach(({ summary }) => {
                const cost = summary.totals.total_cost;
                const isWinner = cost === lowestCost;
                html += `                <td class="${isWinner ? 'winner' : ''}">$${cost.toFixed(4)}</td>\\n`;
            });
            html += `            </tr>\\n`;

            // Duration row
            html += `            <tr>\\n                <td><strong>Total Duration</strong></td>\\n`;
            runData.forEach(({ summary }) => {
                html += `                <td>${(summary.totals.total_duration_ms / 1000).toFixed(1)}s</td>\\n`;
            });
            html += `            </tr>\\n`;

            html += `
        </tbody>
    </table>

    <h2 class="section-title">Category Breakdown</h2>
    <table class="comparison-table">
        <thead>
            <tr>
                <th>Category</th>
`;

            runData.forEach(({ runId }) => {
                html += `                <th>${runId.split('_').pop()}</th>\\n`;
            });

            html += `
            </tr>
        </thead>
        <tbody>
`;

            // Get all unique categories
            const allCategories = new Set();
            runData.forEach(({ summary }) => {
                Object.keys(summary.categories || {}).forEach(cat => allCategories.add(cat));
            });

            // Category rows
            Array.from(allCategories).sort().forEach(category => {
                html += `            <tr>\\n                <td><strong>${category.replace(/_/g, ' ')}</strong></td>\\n`;
                runData.forEach(({ summary }) => {
                    const catData = summary.categories[category];
                    if (catData) {
                        const passRate = catData.pass_rate * 100;
                        html += `                <td>${catData.passed}/${catData.tests} (${passRate.toFixed(0)}%)</td>\\n`;
                    } else {
                        html += `                <td>-</td>\\n`;
                    }
                });
                html += `            </tr>\\n`;
            });

            html += `
        </tbody>
    </table>

    <div style="margin-top: 40px; padding: 20px; background: #e8f4f8; border-radius: 8px; text-align: center;">
        <p style="margin: 0; color: #2c5282; font-size: 14px;">
            <strong>Winner highlighted in green.</strong> Generated: ${new Date().toLocaleString()}
        </p>
    </div>
</body>
</html>
`;

            return html;
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


def generate_empty_index() -> str:
    """Generate index.html when no runs exist."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Agent Evaluation Dashboard - Index</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f7fa;
        }
        .empty-state {
            text-align: center;
            padding: 100px 20px;
            color: #718096;
        }
        .empty-state h2 {
            font-size: 24px;
            margin-bottom: 10px;
            color: #2d3748;
        }
    </style>
</head>
<body>
    <div class="empty-state">
        <h2>No Test Runs Found</h2>
        <p>Run <code>make agent-eval</code> to generate your first test run.</p>
    </div>
</body>
</html>
"""


def main():
    """Generate dashboard from versioned test reports."""
    parser = argparse.ArgumentParser(description="Generate agent evaluation dashboard")
    parser.add_argument(
        "--run-id",
        help="Specific run ID to generate dashboard for (defaults to latest run)"
    )
    parser.add_argument(
        "--output",
        help="Output file path (defaults to database/agent_eval_reports/dashboards/<run_id>.html)"
    )
    args = parser.parse_args()

    base_dir = Path("database/agent_eval_reports")

    if not base_dir.exists():
        print(f"Error: {base_dir} directory not found", file=sys.stderr)
        print("Run 'make agent-eval' first to generate test reports", file=sys.stderr)
        sys.exit(1)

    # Determine which run to use
    if args.run_id:
        run_dir = base_dir / "runs" / args.run_id
        if not run_dir.exists():
            print(f"Error: Run directory not found: {run_dir}", file=sys.stderr)
            sys.exit(1)
    else:
        run_dir = find_latest_run(base_dir)
        if not run_dir:
            print("Error: No test runs found", file=sys.stderr)
            sys.exit(1)

    # Load metadata and results
    metadata = load_run_metadata(run_dir)
    results_by_category = load_test_results(run_dir)

    if not results_by_category:
        print(f"Error: No test results found in {run_dir}", file=sys.stderr)
        sys.exit(1)

    # Generate HTML
    html = generate_html(run_dir, metadata, results_by_category)

    # Determine output file
    if args.output:
        output_file = Path(args.output)
    else:
        dashboards_dir = base_dir / "dashboards"
        dashboards_dir.mkdir(exist_ok=True)
        run_id = metadata.get("run_id", "unknown")
        output_file = dashboards_dir / f"{run_id}.html"

    # Write file
    with open(output_file, "w") as f:
        f.write(html)

    print(f"Dashboard generated: {output_file}")
    print(f"   Run ID: {metadata.get('run_id', 'unknown')}")
    print(f"   Categories: {', '.join(results_by_category.keys())}")
    print(f"   Total tests: {sum(len(tests) for tests in results_by_category.values())}")

    # Also regenerate index.html with all runs
    index_html = generate_index_html(base_dir)
    index_file = base_dir / "dashboards" / "index.html"
    with open(index_file, "w") as f:
        f.write(index_html)
    print(f"Index updated: {index_file}")


if __name__ == "__main__":
    main()
