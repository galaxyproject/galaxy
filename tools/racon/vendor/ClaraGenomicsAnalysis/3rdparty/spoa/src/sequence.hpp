/*!
 * @file sequence.hpp
 *
 * @brief Sequence class header file
 */

#pragma once

#include <cstdint>
#include <memory>
#include <vector>
#include <string>

namespace bioparser {
    template<class T>
    class FastaParser;

    template<class T>
    class FastqParser;
}

namespace spoa {

class Sequence {
public:
    ~Sequence() = default;

    const std::string& name() const {
        return name_;
    }

    const std::string& data() const {
        return data_;
    }

    const std::string& quality() const {
        return quality_;
    }

    friend bioparser::FastaParser<Sequence>;
    friend bioparser::FastqParser<Sequence>;

private:
    Sequence(const char* name, std::uint32_t name_size,
        const char* data, std::uint32_t data_size);
    Sequence(const char* name, std::uint32_t name_size,
        const char* data, std::uint32_t data_size,
        const char* quality, std::uint32_t quality_size);
    Sequence(const Sequence&) = delete;
    const Sequence& operator=(const Sequence&) = delete;

    std::string name_;
    std::string data_;
    std::string quality_;
};

}
