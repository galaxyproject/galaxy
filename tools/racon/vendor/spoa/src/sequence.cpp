/*!
 * @file sequence.cpp
 *
 * @brief Sequence class source file
 */

#include "sequence.hpp"

namespace spoa {

Sequence::Sequence(const char* name, std::uint32_t name_size,
    const char* data, std::uint32_t data_size)
        : name_(name, name_size), data_(data, data_size), quality_(
        data_size, 34) {
}

Sequence::Sequence(const char* name, std::uint32_t name_size,
    const char* data, std::uint32_t data_size,
    const char* quality, std::uint32_t quality_size)
        : name_(name, name_size), data_(data, data_size), quality_(quality,
        quality_size) {
}

}
