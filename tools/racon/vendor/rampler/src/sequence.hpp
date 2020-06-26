/*!
 * @file sequence.hpp
 *
 * @brief Sequence class header file
 */

#pragma once

#include <stdint.h>
#include <string>

namespace bioparser {
    template<class T>
    class FastaParser;

    template<class T>
    class FastqParser;
}

namespace rampler {

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
    Sequence(const char* name, uint32_t name_length, const char* data,
        uint32_t data_length);
    Sequence(const char* name, uint32_t name_length, const char* data,
        uint32_t data_length, const char* quality, uint32_t quality_length);
    Sequence(const Sequence&) = delete;
    const Sequence& operator=(const Sequence&) = delete;

    std::string name_;
    std::string data_;
    std::string quality_;
};

}
