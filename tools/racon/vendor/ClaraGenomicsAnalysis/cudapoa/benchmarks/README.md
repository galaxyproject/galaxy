# CUDA POA Benchmarks

## Single Batch
This benchmark runs a single batch of the graph generation and consensus generation kernels
for varying batches sizes. The intention of this benchmark is to measure the performance
of a single batch of POA.

To run the benchmark, execute
```
./benchmarks/cudapoa/benchmark_cudapoa --benchmark_filter="BM_SingleBatchTest"
```

## Multi Batch
This benchmark runs a large number of POAs (graph followed by consensus generation) over multiple
batches each having varied batch sizes. The intention of this benchmark is to measure performance
of several batched CUDA POA stream that fill up the GPU.

To the the benchmark, execute
```
./benchmarks/cudapoa/benchmark_cudapoa --benchmark_filter="BM_MultiBatchTest"
```
