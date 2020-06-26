/*!
 * @file sampler.hpp
 *
 * @brief Sampler class header file
 */

#pragma once

#include <stdlib.h>
#include <vector>
#include <memory>

namespace bioparser {
    template<class T>
    class Parser;
}

namespace rampler {

class Sampler;
std::unique_ptr<Sampler> createSampler(const std::string& sequences_path);

class Sampler {
public:
    ~Sampler();

    void initialize();

    void subsample(const std::string& out_directory, uint32_t reference_length,
        uint32_t coverage);

    void split(const std::string& out_directory, uint32_t chunk_size);

    friend std::unique_ptr<Sampler> createSampler(const std::string& sequences_path);
private:
    Sampler(std::unique_ptr<bioparser::Parser<Sequence>> sparser,
        const std::string& base_name, const std::string& extension);
    Sampler(const Sampler&) = delete;
    const Sampler& operator=(const Sampler&) = delete;

    std::unique_ptr<bioparser::Parser<Sequence>> sparser_;
    uint64_t sequences_length_;
    std::string base_name_;
    std::string extension_;
};

}
