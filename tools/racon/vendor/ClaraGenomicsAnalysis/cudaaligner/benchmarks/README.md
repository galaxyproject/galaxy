# CUDA Aligner Benchmarks

## Single Alignment
This benchmark runs a single alignment between a pair of simulated sequences
of varying batches sizes. The intention of this benchmark is to measure the performance
of a single alignment in CUDA.

To run the benchmark, execute
```
./benchmarks/cudaaligner/benchmark_cudaaligner --benchmark_filter="BM_SingleAlignment"
```

## Single Batch Alignment
This benchmark runs a varying number of alignments within a single batch, each of varying string
sizes. The intention of this benchmark is to measure performanceo of batched alignment.

To the the benchmark, execute
```
./benchmarks/cudaaligner/benchmark_cudaaligner --benchmark_filter="BM_SingleBatchAlignment"
```
