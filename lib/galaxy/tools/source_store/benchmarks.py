"""
Benchmarks for tool source deserialization.

Run with: python -m galaxy.tools.source_store.benchmarks
"""

import hashlib
import json
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from galaxy.tool_util.parser.factory import TOOL_SOURCE_FACTORIES
from .index import (
    ToolIndex,
    ToolIndexEntry,
)


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""

    name: str
    iterations: int
    total_time_ms: float
    mean_time_ms: float
    median_time_ms: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    throughput_per_sec: float


def benchmark_function(
    name: str,
    func: Callable,
    iterations: int = 100,
    warmup: int = 10,
) -> BenchmarkResult:
    """
    Benchmark a function.

    Args:
        name: Name of the benchmark.
        func: Function to benchmark.
        iterations: Number of iterations.
        warmup: Number of warmup iterations.

    Returns:
        Benchmark result.
    """
    # Warmup
    for _ in range(warmup):
        func()

    # Actual benchmark
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms

    total_time = sum(times)
    return BenchmarkResult(
        name=name,
        iterations=iterations,
        total_time_ms=total_time,
        mean_time_ms=statistics.mean(times),
        median_time_ms=statistics.median(times),
        min_time_ms=min(times),
        max_time_ms=max(times),
        std_dev_ms=statistics.stdev(times) if len(times) > 1 else 0,
        throughput_per_sec=iterations / (total_time / 1000) if total_time > 0 else 0,
    )


class ToolSourceBenchmarks:
    """Benchmark suite for tool source operations."""

    def __init__(self, tool_sources_dir: Path | None = None):
        """
        Initialize benchmarks.

        Args:
            tool_sources_dir: Directory containing tool XML files.
        """
        self.tool_sources_dir = tool_sources_dir or self._find_tool_sources()
        self._cached_sources: dict[str, str] = {}

    def _find_tool_sources(self) -> Path:
        """Find Galaxy tools directory."""
        candidates = [
            Path("tools"),
            Path("lib/galaxy/tools/bundled"),
            Path(__file__).parent.parent.parent.parent / "tools" / "bundled",
            Path(__file__).parent.parent.parent.parent / "tools",
        ]
        for p in candidates:
            if p.exists():
                return p
        # Return first candidate even if doesn't exist
        return candidates[0]

    def _load_sample_tools(self, count: int = 50) -> list[tuple]:
        """Load sample tool XML files."""
        tools: list[tuple] = []
        if not self.tool_sources_dir.exists():
            return tools

        for xml_file in self.tool_sources_dir.rglob("*.xml"):
            if len(tools) >= count:
                break
            try:
                with open(xml_file) as f:
                    content = f.read()
                if "<tool" in content:
                    tools.append((str(xml_file), content))
            except Exception:
                continue
        return tools

    def _build_sample_index(self, count: int) -> ToolIndex:
        """Build a realistic sample index for benchmarking."""
        index = ToolIndex()
        for i in range(count):
            index.entries[f"tool_{i}"] = ToolIndexEntry(
                id=f"tool_{i}",
                name=f"Tool Number {i}",
                version=f"1.{i % 10}.0",
                description=f"A tool that does thing {i}",
                labels=["genomics", "ngs"] if i % 2 == 0 else ["proteomics"],
                test_count=i % 5,
                requirements=[
                    {"name": f"dep_{i % 20}", "version": "1.0", "type": "package"},
                    {"name": f"dep_{(i + 1) % 20}", "version": "2.0", "type": "package"},
                ],
                container_requirements=(
                    [{"type": "docker", "identifier": f"biocontainers/tool_{i % 50}:latest"}] if i % 3 == 0 else []
                ),
                tool_shed="toolshed.g2.bx.psu.edu" if i % 4 == 0 else None,
                repository_name=f"repo_{i % 100}" if i % 4 == 0 else None,
                repository_owner=f"owner_{i % 10}" if i % 4 == 0 else None,
                is_local=(i % 4 != 0),
                panel_section_id=f"section_{i % 10}",
                panel_section_name=f"Section {i % 10}",
            )
            # Update by_section
            section_id = f"section_{i % 10}"
            if section_id not in index.by_section:
                index.by_section[section_id] = []
            index.by_section[section_id].append(f"tool_{i}")

        return index

    def benchmark_xml_parsing(self, iterations: int = 100) -> BenchmarkResult | None:
        """Benchmark XML tool source parsing from string."""
        tools = self._load_sample_tools(10)
        if not tools:
            print("No tools found for XML parsing benchmark")
            return None

        # Use a representative tool
        path, content = tools[0]
        factory = TOOL_SOURCE_FACTORIES.get("XmlToolSource")
        if not factory:
            print("XmlToolSource factory not found")
            return None

        return benchmark_function(
            name="xml_parsing",
            func=lambda: factory(content),
            iterations=iterations,
        )

    def benchmark_deserialization_from_db_format(self, iterations: int = 100) -> BenchmarkResult | None:
        """Benchmark deserializing from database JSON format."""
        tools = self._load_sample_tools(10)
        if not tools:
            print("No tools found for deserialization benchmark")
            return None

        path, content = tools[0]

        # Simulate DB storage format
        db_format = json.dumps(
            {
                "raw": content,
                "tool_source_class": "XmlToolSource",
            }
        )

        factory = TOOL_SOURCE_FACTORIES.get("XmlToolSource")
        if not factory:
            return None

        def deserialize():
            data = json.loads(db_format)
            return factory(data["raw"])

        return benchmark_function(
            name="db_deserialization",
            func=deserialize,
            iterations=iterations,
        )

    def benchmark_hash_computation(self, iterations: int = 1000) -> BenchmarkResult | None:
        """Benchmark content hash computation."""
        tools = self._load_sample_tools(10)
        if not tools:
            # Use a sample string
            content = "<tool id='test'><command>echo hello</command></tool>" * 100
        else:
            path, content = tools[0]

        return benchmark_function(
            name="hash_computation",
            func=lambda: hashlib.sha256(content.encode()).hexdigest(),
            iterations=iterations,
        )

    def benchmark_api_response_generation(self, iterations: int = 100) -> BenchmarkResult:
        """Benchmark generating /api/tools response from index."""
        index = self._build_sample_index(1000)

        def generate_response():
            return [e.to_api_dict() for e in index.entries.values()]

        return benchmark_function("api_response_generation", generate_response, iterations)

    def benchmark_tests_summary(self, iterations: int = 100) -> BenchmarkResult:
        """Benchmark /api/tools/tests_summary generation."""
        index = self._build_sample_index(1000)

        return benchmark_function(
            "tests_summary",
            lambda: index.get_tests_summary(),
            iterations,
        )

    def benchmark_all_requirements(self, iterations: int = 100) -> BenchmarkResult:
        """Benchmark /api/tools/all_requirements generation."""
        index = self._build_sample_index(1000)
        # Clear cache to measure actual computation
        index._requirements_cache = None

        def get_reqs():
            index._requirements_cache = None
            return index.get_all_requirements()

        return benchmark_function(
            "all_requirements",
            get_reqs,
            iterations,
        )

    def benchmark_requirements_summary(self, iterations: int = 100) -> BenchmarkResult:
        """Benchmark /api/dependency_resolvers/toolbox generation."""
        index = self._build_sample_index(1000)

        return benchmark_function(
            "requirements_summary_by_req",
            lambda: index.get_requirements_summary(index_by="requirements"),
            iterations,
        )

    def benchmark_index_serialization(self, iterations: int = 50) -> BenchmarkResult:
        """Benchmark index to_dict serialization."""
        index = self._build_sample_index(1000)

        return benchmark_function(
            "index_serialization",
            lambda: index.to_dict(),
            iterations,
        )

    def benchmark_index_deserialization(self, iterations: int = 50) -> BenchmarkResult:
        """Benchmark index from_dict deserialization."""
        index = self._build_sample_index(1000)
        data = index.to_dict()

        return benchmark_function(
            "index_deserialization",
            lambda: ToolIndex.from_dict(data),
            iterations,
        )

    def run_all(self, iterations: int = 100) -> list[BenchmarkResult]:
        """Run all benchmarks."""
        results = []

        print("Running tool source benchmarks...")
        print(f"Iterations per benchmark: {iterations}")
        print("-" * 60)

        benchmarks = [
            ("XML Parsing", lambda: self.benchmark_xml_parsing(iterations)),
            ("DB Deserialization", lambda: self.benchmark_deserialization_from_db_format(iterations)),
            ("Hash Computation", lambda: self.benchmark_hash_computation(iterations * 10)),
            ("API Response Generation", lambda: self.benchmark_api_response_generation(iterations)),
            ("Tests Summary", lambda: self.benchmark_tests_summary(iterations)),
            ("All Requirements", lambda: self.benchmark_all_requirements(iterations)),
            ("Requirements Summary", lambda: self.benchmark_requirements_summary(iterations)),
            ("Index Serialization", lambda: self.benchmark_index_serialization(iterations // 2)),
            ("Index Deserialization", lambda: self.benchmark_index_deserialization(iterations // 2)),
        ]

        for name, bench_func in benchmarks:
            try:
                result = bench_func()
                if result:
                    results.append(result)
                    print(f"\n{result.name}:")
                    print(f"  Mean:       {result.mean_time_ms:.3f} ms")
                    print(f"  Median:     {result.median_time_ms:.3f} ms")
                    print(f"  Min/Max:    {result.min_time_ms:.3f} / {result.max_time_ms:.3f} ms")
                    print(f"  Std Dev:    {result.std_dev_ms:.3f} ms")
                    print(f"  Throughput: {result.throughput_per_sec:.1f} ops/sec")
            except Exception as e:
                print(f"\n{name}: FAILED - {e}")

        return results


def main():
    """Run benchmarks from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Tool source benchmarks")
    parser.add_argument("--iterations", "-n", type=int, default=100)
    parser.add_argument("--tools-dir", type=Path, default=None)
    parser.add_argument("--output", "-o", type=Path, default=None)

    args = parser.parse_args()

    benchmarks = ToolSourceBenchmarks(args.tools_dir)
    results = benchmarks.run_all(args.iterations)

    if args.output:
        with open(args.output, "w") as f:
            json.dump([r.__dict__ for r in results], f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
