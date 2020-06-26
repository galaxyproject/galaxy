// Implementation file for CUDA POA utilities.

#pragma once

#include <stdlib.h>
#include <cuda_runtime_api.h>

namespace racon {

void cudaCheckError(std::string &msg)
{
    cudaError_t error = cudaGetLastError();
    if (error != cudaSuccess)
    {
        fprintf(stderr, "%s (CUDA error %s)\n", msg.c_str(), cudaGetErrorString(error));
        exit(-1);
    }
}

} // namespace racon
