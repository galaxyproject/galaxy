/*!
 * @file window.hpp
 *
 * @brief Window class header file
 */

#pragma once

#include <stdlib.h>
#include <vector>
#include <memory>
#include <string>
#include <utility>

namespace spoa {
    class AlignmentEngine;
}

namespace racon {

enum class WindowType {
    kNGS, // Next Generation Sequencing
    kTGS // Third Generation Sequencing
};

class Window;
std::shared_ptr<Window> createWindow(uint64_t id, uint32_t rank, WindowType type,
    const char* backbone, uint32_t backbone_length, const char* quality,
    uint32_t quality_length);

class Window {

public:
    ~Window();

    uint64_t id() const {
        return id_;
    }
    uint32_t rank() const {
        return rank_;
    }

    const std::string& consensus() const {
        return consensus_;
    }

    bool generate_consensus(std::shared_ptr<spoa::AlignmentEngine> alignment_engine,
        bool trim);

    void add_layer(const char* sequence, uint32_t sequence_length,
        const char* quality, uint32_t quality_length, uint32_t begin,
        uint32_t end);

    friend std::shared_ptr<Window> createWindow(uint64_t id, uint32_t rank,
        WindowType type, const char* backbone, uint32_t backbone_length,
        const char* quality, uint32_t quality_length);

#ifdef CUDA_ENABLED
    friend class CUDABatchProcessor;
#endif
private:
    Window(uint64_t id, uint32_t rank, WindowType type, const char* backbone,
        uint32_t backbone_length, const char* quality, uint32_t quality_length);
    Window(const Window&) = delete;
    const Window& operator=(const Window&) = delete;

    uint64_t id_;
    uint32_t rank_;
    WindowType type_;
    std::string consensus_;
    std::vector<std::pair<const char*, uint32_t>> sequences_;
    std::vector<std::pair<const char*, uint32_t>> qualities_;
    std::vector<std::pair<uint32_t, uint32_t>> positions_;
};

}
