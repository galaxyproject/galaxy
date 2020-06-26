/*!
 * @file bioparser.hpp
 *
 * @brief Bioparser header file
 */

#pragma once

#include <cstdint>
#include <exception>
#include <memory>
#include <string>
#include <vector>

#include "zlib.h"

namespace bioparser {

static const std::string version = "v2.0.0";

constexpr std::uint32_t kBufferSize = 64 * 1024;

// Small/Medium/Large Storage Size
constexpr std::uint32_t kSSS = 4 * 1024;
constexpr std::uint32_t kMSS = 8 * 1024 * 1024;
constexpr std::uint32_t kLSS = 512 * 1024 * 1024;

/*!
 * @brief Parser absctract class
 */
template<class T>
class Parser;

template<template<class> class P, class T>
std::unique_ptr<Parser<T>> createParser(const std::string& path);

/*!
 * @brief Parser specializations
 */
template<class T>
class FastaParser;

template<class T>
class FastqParser;

template<class T>
class MhapParser;

template<class T>
class PafParser;

template<class T>
class SamParser;

/*!
 * @brief Parser definitions
 */
template<class T>
class Parser {
public:
    virtual ~Parser() = 0;

    void reset();

    virtual bool parse(std::vector<std::unique_ptr<T>>& dst,
        std::uint64_t max_bytes, bool trim = true) = 0;

    bool parse(std::vector<std::shared_ptr<T>>& dst, std::uint64_t max_bytes,
        bool trim = true);

protected:
    Parser(gzFile input_file, std::uint32_t storage_size);
    Parser(const Parser&) = delete;
    const Parser& operator=(const Parser&) = delete;

    std::unique_ptr<gzFile_s, int(*)(gzFile)> input_file_;
    std::vector<char> buffer_;
    std::vector<char> storage_;
};

template<class T>
class FastaParser: public Parser<T> {
public:
    ~FastaParser();

    bool parse(std::vector<std::unique_ptr<T>>& dst,
        std::uint64_t max_bytes, bool trim = true) override;

    friend std::unique_ptr<Parser<T>>
        createParser<bioparser::FastaParser, T>(const std::string& path);

private:
    FastaParser(gzFile input_file);
    FastaParser(const FastaParser&) = delete;
    const FastaParser& operator=(const FastaParser&) = delete;
};

template<class T>
class FastqParser: public Parser<T> {
public:
    ~FastqParser();

    bool parse(std::vector<std::unique_ptr<T>>& dst,
        std::uint64_t max_bytes, bool trim = true) override;

    friend std::unique_ptr<Parser<T>>
        createParser<bioparser::FastqParser, T>(const std::string& path);

private:
    FastqParser(gzFile input_file);
    FastqParser(const FastqParser&) = delete;
    const FastqParser& operator=(const FastqParser&) = delete;
};

template<class T>
class MhapParser: public Parser<T> {
public:
    ~MhapParser();

    bool parse(std::vector<std::unique_ptr<T>>& dst,
        std::uint64_t max_bytes, bool trim = true) override;

    friend std::unique_ptr<Parser<T>>
        createParser<bioparser::MhapParser, T>(const std::string& path);

private:
    MhapParser(gzFile input_file);
    MhapParser(const MhapParser&) = delete;
    const MhapParser& operator=(const MhapParser&) = delete;
};

template<class T>
class PafParser: public Parser<T> {
public:
    ~PafParser();

    bool parse(std::vector<std::unique_ptr<T>>& dst,
        std::uint64_t max_bytes, bool trim = true) override;

    friend std::unique_ptr<Parser<T>>
        createParser<bioparser::PafParser, T>(const std::string& path);

private:
    PafParser(gzFile input_file);
    PafParser(const PafParser&) = delete;
    const PafParser& operator=(const PafParser&) = delete;
};

template<class T>
class SamParser: public Parser<T> {
public:
    ~SamParser();

    bool parse(std::vector<std::unique_ptr<T>>& dst,
        std::uint64_t max_bytes, bool trim = true) override;

    friend std::unique_ptr<Parser<T>>
        createParser<bioparser::SamParser, T>(const std::string& path);

private:
    SamParser(gzFile input_file);
    SamParser(const SamParser&) = delete;
    const SamParser& operator=(const SamParser&) = delete;
};

/*!
 * @brief Implementation
 */
inline void rightStrip(const char* src, std::uint32_t& src_length) {
    while (src_length > 0 && isspace(src[src_length - 1])) {
        --src_length;
    }
}

inline void rightStripHard(const char* src, std::uint32_t& src_length) {
    for (std::uint32_t i = 0; i < src_length; ++i) {
        if (isspace(src[i])) {
            src_length = i;
            break;
        }
    }
}

template<template<class> class P, class T>
inline std::unique_ptr<Parser<T>> createParser(const std::string& path) {

    auto input_file = gzopen(path.c_str(), "r");
    if (input_file == nullptr) {
        throw std::invalid_argument("[bioparser::createParser] error: "
            "unable to open file " + path + "!");
    }

    return std::unique_ptr<Parser<T>>(new P<T>(input_file));
}

template<class T>
inline Parser<T>::Parser(gzFile input_file, std::uint32_t storage_size)
        : input_file_(input_file, gzclose), buffer_(kBufferSize, 0),
        storage_(storage_size, 0) {
}

template<class T>
inline Parser<T>::~Parser() {
}

template<class T>
inline void Parser<T>::reset() {
    gzseek(this->input_file_.get(), 0, SEEK_SET);
}

template<class T>
inline bool Parser<T>::parse(std::vector<std::shared_ptr<T>>& dst,
    std::uint64_t max_bytes, bool trim) {

    std::vector<std::unique_ptr<T>> tmp;
    auto ret = this->parse_objects(tmp, max_bytes, trim);

    dst.reserve(dst.size() + tmp.size());
    for (auto& it: tmp) {
        dst.emplace_back(std::move(it));
    }
    return ret;
}

template<class T>
inline FastaParser<T>::FastaParser(gzFile input_file)
        : Parser<T>(input_file, kSSS + kMSS) {
}

template<class T>
inline FastaParser<T>::~FastaParser() {
}

template<class T>
inline bool FastaParser<T>::parse(std::vector<std::unique_ptr<T>>& dst,
    std::uint64_t max_bytes, bool trim) {

    auto input_file = this->input_file_.get();
    bool is_end = gzeof(input_file);
    bool is_valid = false;
    bool status = false;
    std::uint64_t current_bytes = 0;
    std::uint64_t total_bytes = 0;
    std::uint64_t num_objects = 0;
    std::uint64_t last_object_id = num_objects;
    std::uint32_t line_number = 0;

    char* name = &(this->storage_[0]);
    std::uint32_t name_length = 0;

    char* sequence = &(this->storage_[kSSS]);
    std::uint32_t sequence_length = 0;

    while (!is_end) {

        std::uint64_t read_bytes = gzfread(this->buffer_.data(), sizeof(char),
            this->buffer_.size(), input_file);
        is_end = gzeof(input_file);

        total_bytes += read_bytes;
        if (max_bytes != 0 && total_bytes > max_bytes) {
            if (last_object_id == num_objects) {
                throw std::invalid_argument("[bioparser::FastaParser] error: "
                    "too small chunk size!");
            }
            gzseek(input_file, -(current_bytes + read_bytes), SEEK_CUR);
            status = true;
            break;
        }

        for (std::uint32_t i = 0; i < read_bytes; ++i) {
            auto c = this->buffer_[i];

            if (c == '\n') {
                ++line_number;
            } else if (c == '>' && line_number != 0) {
                is_valid = true;
                line_number = 0;
            } else {
                switch (line_number) {
                    case 0:
                        if (name_length < kSSS) {
                            if (!(name_length == 0 && isspace(c))) {
                                name[name_length++] = c;
                            }
                        }
                        break;
                    default:
                        sequence[sequence_length++] = c;
                        if (sequence_length == kMSS) {
                            this->storage_.resize(kSSS + kLSS, 0);
                            name = &(this->storage_[0]);
                            sequence = &(this->storage_[kSSS]);
                        }
                        break;
                }
            }

            ++current_bytes;

            if (is_valid || (is_end && i == read_bytes - 1)) {
                if (trim) {
                    rightStripHard(name, name_length);
                } else {
                    rightStrip(name, name_length);
                }
                rightStrip(sequence, sequence_length);

                if (name_length == 0 || name[0] != '>' || sequence_length == 0) {
                    throw std::invalid_argument("[bioparser::FastaParser] error: "
                        "invalid file format!");
                }

                dst.emplace_back(std::unique_ptr<T>(new T(
                    (const char*) &(name[1]), name_length - 1,
                    (const char*) sequence, sequence_length)));

                ++num_objects;
                current_bytes = 1;
                name_length = 1;
                sequence_length = 0;
                is_valid = false;
            }
        }
    }

    return status;
}

template<class T>
inline FastqParser<T>::FastqParser(gzFile input_file)
        : Parser<T>(input_file, kSSS + 2 * kMSS) {
}

template<class T>
inline FastqParser<T>::~FastqParser() {
}

template<class T>
inline bool FastqParser<T>::parse(std::vector<std::unique_ptr<T>>& dst,
    std::uint64_t max_bytes, bool trim) {

    auto input_file = this->input_file_.get();
    bool is_end = gzeof(input_file);
    bool is_valid = false;
    bool status = false;
    std::uint64_t current_bytes = 0;
    std::uint64_t total_bytes = 0;
    std::uint64_t num_objects = 0;
    std::uint64_t last_object_id = num_objects;
    std::uint32_t line_number = 0;

    char* name = &(this->storage_[0]);
    std::uint32_t name_length = 0;

    char* sequence = &(this->storage_[kSSS]);
    std::uint32_t sequence_length = 0;

    char* quality = &(this->storage_[kSSS + kMSS]);
    std::uint32_t quality_length = 0;

    while (!is_end) {

        std::uint64_t read_bytes = gzfread(this->buffer_.data(), sizeof(char),
            this->buffer_.size(), input_file);
        is_end = gzeof(input_file);

        total_bytes += read_bytes;
        if (max_bytes != 0 && total_bytes > max_bytes) {
            if (last_object_id == num_objects) {
                throw std::invalid_argument("[bioparser::FastqParser] error: "
                    "too small chunk size!");
            }
            gzseek(input_file, -(current_bytes + read_bytes), SEEK_CUR);
            status = true;
            break;
        }

        for (std::uint32_t i = 0; i < read_bytes; ++i) {
            auto c = this->buffer_[i];

            if (c == '\n') {
                if (!(line_number == 1 || (line_number == 3 && quality_length < sequence_length))) {
                    line_number = (line_number + 1) % 4;
                    if (line_number == 0) {
                        is_valid = true;
                    }
                }
            } else if (line_number == 1 && c == '+') {
                line_number = 2;
            } else {
                switch (line_number) {
                    case 0:
                        if (name_length < kSSS) {
                            if (!(name_length == 0 && isspace(c))) {
                                name[name_length++] = c;
                            }
                        }
                        break;
                    case 1:
                        sequence[sequence_length++] = c;
                        if (sequence_length == kMSS) {
                            this->storage_.resize(kSSS + 2 * kLSS, 0);
                            name = &(this->storage_[0]);
                            sequence = &(this->storage_[kSSS]);
                            quality = &(this->storage_[kSSS + kLSS]);
                        }
                        break;
                    case 2:
                        // comment line starting with '+'
                        // do nothing
                        break;
                    case 3:
                        quality[quality_length++] = c;
                        break;
                    default:
                        // never reaches this case
                        break;
                }
            }

            ++current_bytes;

            if (is_valid || (is_end && i == read_bytes - 1)) {
                if (trim) {
                    rightStripHard(name, name_length);
                } else {
                    rightStrip(name, name_length);
                }
                rightStrip(sequence, sequence_length);
                rightStrip(quality, quality_length);

                if (name_length == 0 || name[0] != '@' || sequence_length == 0 ||
                    quality_length == 0 || sequence_length != quality_length) {
                    throw std::invalid_argument("[bioparser::FastqParser] error: "
                        "invalid file format!");
                }

                dst.emplace_back(std::unique_ptr<T>(new T(
                    (const char*) &(name[1]), name_length - 1,
                    (const char*) sequence, sequence_length,
                    (const char*) quality, quality_length)));

                ++num_objects;
                current_bytes = 0;
                name_length = 0;
                sequence_length = 0;
                quality_length = 0;
                is_valid = false;
            }
        }
    }

    return status;
}

template<class T>
inline MhapParser<T>::MhapParser(gzFile input_file)
        : Parser<T>(input_file, kSSS) {
}

template<class T>
inline MhapParser<T>::~MhapParser() {
}

template<class T>
inline bool MhapParser<T>::parse(std::vector<std::unique_ptr<T>>& dst,
    std::uint64_t max_bytes, bool) {

    auto input_file = this->input_file_.get();
    bool is_end = gzeof(input_file);
    bool status = false;
    std::uint64_t current_bytes = 0;
    std::uint64_t total_bytes = 0;
    std::uint64_t num_objects = 0;
    std::uint64_t last_object_id = num_objects;

    const std::uint32_t kMhapObjectLength = 12;

    char* line = &(this->storage_[0]);
    std::uint32_t line_length = 0;

    std::uint64_t a_id = 0, b_id = 0;
    std::uint32_t a_rc = 0, a_begin = 0, a_end = 0, a_length = 0, b_rc = 0,
        b_begin = 0, b_end = 0, b_length = 0, minmers = 0;
    double error = 0;

    while (!is_end) {

        std::uint64_t read_bytes = gzfread(this->buffer_.data(), sizeof(char),
            this->buffer_.size(), input_file);
        is_end = gzeof(input_file);

        total_bytes += read_bytes;
        if (max_bytes != 0 && total_bytes > max_bytes) {
            if (last_object_id == num_objects) {
                throw std::invalid_argument("[bioparser::MhapParser] error: "
                    "too small chunk size!");
            }
            gzseek(input_file, -(current_bytes + read_bytes), SEEK_CUR);
            status = true;
            break;
        }

        for (std::uint32_t i = 0; i < read_bytes; ++i) {

            auto c = this->buffer_[i];
            ++current_bytes;

            if (c == '\n' || (is_end && i == read_bytes - 1)) {

                line[line_length] = 0;
                rightStrip(line, line_length);

                std::uint32_t num_values = 0, begin = 0;
                while (true) {
                    std::uint32_t end = begin;
                    for (std::uint32_t j = begin; j < line_length; ++j) {
                        if (line[j] == ' ') {
                            end = j;
                            break;
                        }
                    }
                    if (end == begin) {
                        end = line_length;
                    }
                    line[end] = 0;

                    switch (num_values) {
                        case 0: a_id = atoll(&line[begin]); break;
                        case 1: b_id = atoll(&line[begin]); break;
                        case 2: error = atof(&line[begin]); break;
                        case 3: minmers = atoi(&line[begin]); break;
                        case 4: a_rc = atoi(&line[begin]); break;
                        case 5: a_begin = atoi(&line[begin]); break;
                        case 6: a_end = atoi(&line[begin]); break;
                        case 7: a_length = atoi(&line[begin]); break;
                        case 8: b_rc = atoi(&line[begin]); break;
                        case 9: b_begin = atoi(&line[begin]); break;
                        case 10: b_end = atoi(&line[begin]); break;
                        case 11: b_length = atoi(&line[begin]); break;
                        default: break;
                    }
                    num_values++;
                    if (end == line_length || num_values == kMhapObjectLength) {
                        break;
                    }
                    begin = end + 1;
                }

                if (num_values != kMhapObjectLength) {
                    throw std::invalid_argument("[bioparser::MhapParser] error: "
                        "invalid file format!");
                }

                dst.emplace_back(std::unique_ptr<T>(new T(a_id, b_id, error,
                    minmers, a_rc, a_begin, a_end, a_length, b_rc, b_begin,
                    b_end, b_length)));

                ++num_objects;
                current_bytes = 0;
                line_length = 0;
            } else {
                line[line_length++] = c;
            }
        }
    }

    return status;
}

template<class T>
inline PafParser<T>::PafParser(gzFile input_file)
        : Parser<T>(input_file, 3 * kSSS + kMSS) {
}

template<class T>
inline PafParser<T>::~PafParser() {
}

template<class T>
inline bool PafParser<T>::parse(std::vector<std::unique_ptr<T>>& dst,
    std::uint64_t max_bytes, bool trim) {

    auto input_file = this->input_file_.get();
    bool is_end = gzeof(input_file);
    bool status = false;
    std::uint64_t current_bytes = 0;
    std::uint64_t total_bytes = 0;
    std::uint64_t num_objects = 0;
    std::uint64_t last_object_id = num_objects;

    const std::uint32_t kPafObjectLength = 12;

    char* line = &(this->storage_[0]);
    std::uint32_t line_length = 0;

    const char* q_name = nullptr, * t_name = nullptr;

    std::uint32_t q_name_length = 0, q_length = 0, q_begin = 0, q_end = 0,
        t_name_length = 0, t_length = 0, t_begin = 0, t_end = 0,
        matching_bases = 0, overlap_length = 0, mapping_quality = 0;
    char orientation = '\0';

    while (!is_end) {

        std::uint64_t read_bytes = gzfread(this->buffer_.data(), sizeof(char),
            this->buffer_.size(), input_file);
        is_end = gzeof(input_file);

        total_bytes += read_bytes;
        if (max_bytes != 0 && total_bytes > max_bytes) {
            if (last_object_id == num_objects) {
                throw std::invalid_argument("[bioparser::PafParser] error: "
                    "too small chunk size!");
            }
            gzseek(input_file, -(current_bytes + read_bytes), SEEK_CUR);
            status = true;
            break;
        }

        for (std::uint32_t i = 0; i < read_bytes; ++i) {

            auto c = this->buffer_[i];
            ++current_bytes;

            if (c == '\n' || (is_end && i == read_bytes - 1)) {

                line[line_length] = 0;
                rightStrip(line, line_length);

                std::uint32_t num_values = 0, begin = 0;
                while (true) {
                    std::uint32_t end = begin;
                    for (std::uint32_t j = begin; j < line_length; ++j) {
                        if (line[j] == '\t') {
                            end = j;
                            break;
                        }
                    }
                    if (end == begin) {
                        end = line_length;
                    }
                    line[end] = 0;

                    switch (num_values) {
                        case 0:
                            q_name = &line[begin];
                            q_name_length = end - begin;
                            break;
                        case 1: q_length = atoi(&line[begin]); break;
                        case 2: q_begin = atoi(&line[begin]); break;
                        case 3: q_end = atoi(&line[begin]); break;
                        case 4: orientation = line[begin]; break;
                        case 5:
                            t_name = &line[begin];
                            t_name_length = end - begin;
                            break;
                        case 6: t_length = atoi(&line[begin]); break;
                        case 7: t_begin = atoi(&line[begin]); break;
                        case 8: t_end = atoi(&line[begin]); break;
                        case 9: matching_bases = atoi(&line[begin]); break;
                        case 10: overlap_length = atoi(&line[begin]); break;
                        case 11: mapping_quality = atoi(&line[begin]); break;
                        default: break;
                    }
                    num_values++;
                    if (end == line_length || num_values == kPafObjectLength) {
                        break;
                    }
                    begin = end + 1;
                }

                if (num_values != kPafObjectLength) {
                    throw std::invalid_argument("[bioparser::PafParser] error: "
                        "invalid file format!");
                }

                q_name_length = std::min(q_name_length, kSSS);
                t_name_length = std::min(t_name_length, kSSS);

                if (trim) {
                    rightStripHard(q_name, q_name_length);
                    rightStripHard(t_name, t_name_length);
                } else {
                    rightStrip(q_name, q_name_length);
                    rightStrip(t_name, t_name_length);
                }

                if (q_name_length == 0 || t_name_length == 0) {
                    throw std::invalid_argument("[bioparser::PafParser] error: "
                        "invalid file format!");
                }

                dst.emplace_back(std::unique_ptr<T>(new T(q_name, q_name_length,
                    q_length, q_begin, q_end, orientation, t_name, t_name_length,
                    t_length, t_begin, t_end, matching_bases, overlap_length,
                    mapping_quality)));

                ++num_objects;
                current_bytes = 0;
                line_length = 0;
            } else {
                line[line_length++] = c;
                if (line_length == this->storage_.size()) {
                    this->storage_.resize(3 * kSSS + kLSS);
                    line = &(this->storage_[0]);
                }
            }
        }
    }

    return status;
}

template<class T>
inline SamParser<T>::SamParser(gzFile input_file)
        : Parser<T>(input_file, 5 * kSSS + 2 * kMSS) {
}

template<class T>
inline SamParser<T>::~SamParser() {
}

template<class T>
inline bool SamParser<T>::parse(std::vector<std::unique_ptr<T>>& dst,
    std::uint64_t max_bytes, bool trim) {

    auto input_file = this->input_file_.get();
    bool is_end = gzeof(input_file);
    bool status = false;
    std::uint64_t current_bytes = 0;
    std::uint64_t total_bytes = 0;
    std::uint64_t num_objects = 0;
    std::uint64_t last_object_id = num_objects;

    const std::uint32_t kSamObjectLength = 11;

    char* line = &(this->storage_[0]);
    std::uint32_t line_length = 0;

    const char* q_name = nullptr, * t_name = nullptr, * cigar = nullptr,
        * t_next_name = nullptr, * sequence = nullptr, * quality = nullptr;

    std::uint32_t q_name_length = 0, flag = 0, t_name_length = 0, t_begin = 0,
        mapping_quality = 0, cigar_length = 0, t_next_name_length = 0,
        t_next_begin = 0, template_length = 0, sequence_length = 0,
        quality_length = 0;

    while (!is_end) {

        std::uint64_t read_bytes = gzfread(this->buffer_.data(), sizeof(char),
            this->buffer_.size(), input_file);
        is_end = gzeof(input_file);

        total_bytes += read_bytes;
        if (max_bytes != 0 && total_bytes > max_bytes) {
            if (last_object_id == num_objects) {
                throw std::invalid_argument("[bioparser::SamParser] error: "
                    "too small chunk size!");
            }
            gzseek(input_file, -(current_bytes + read_bytes), SEEK_CUR);
            status = true;
            break;
        }

        for (std::uint32_t i = 0; i < read_bytes; ++i) {

            auto c = this->buffer_[i];
            ++current_bytes;

            if (c == '\n' || (is_end && i == read_bytes - 1)) {

                if (line[0] == '@') {
                    line_length = 0;
                    current_bytes = 0;
                    continue;
                }

                line[line_length] = 0;
                rightStrip(line, line_length);

                std::uint32_t num_values = 0, begin = 0;
                while (true) {
                    std::uint32_t end = begin;
                    for (std::uint32_t j = begin; j < line_length; ++j) {
                        if (line[j] == '\t') {
                            end = j;
                            break;
                        }
                    }
                    if (end == begin) {
                        end = line_length;
                    }
                    line[end] = 0;

                    switch (num_values) {
                        case 0:
                            q_name = &line[begin];
                            q_name_length = end - begin;
                            break;
                        case 1: flag = atoi(&line[begin]); break;
                        case 2:
                            t_name = &line[begin];
                            t_name_length = end - begin;
                            break;
                        case 3: t_begin = atoi(&line[begin]); break;
                        case 4: mapping_quality = atoi(&line[begin]); break;
                        case 5:
                            cigar = &line[begin];
                            cigar_length = end - begin;
                            break;
                        case 6:
                            t_next_name = &line[begin];
                            t_next_name_length = end - begin;
                            break;
                        case 7: t_next_begin = atoi(&line[begin]); break;
                        case 8: template_length = atoi(&line[begin]); break;
                        case 9:
                            sequence = &line[begin];
                            sequence_length = end - begin;
                            break;
                        case 10:
                            quality = &line[begin];
                            quality_length = end - begin;
                            break;
                        default: break;
                    }
                    num_values++;
                    if (end == line_length || num_values == kSamObjectLength) {
                        break;
                    }
                    begin = end + 1;
                }

                if (num_values != kSamObjectLength) {
                    throw std::invalid_argument("[bioparser::SamParser] error: "
                        "invalid file format!");
                }

                q_name_length = std::min(q_name_length, kSSS);
                t_name_length = std::min(t_name_length, kSSS);
                t_next_name_length = std::min(t_next_name_length, kSSS);

                if (trim) {
                    rightStripHard(q_name, q_name_length);
                    rightStripHard(t_name, t_name_length);
                    rightStripHard(t_next_name, t_next_name_length);
                } else {
                    rightStrip(q_name, q_name_length);
                    rightStrip(t_name, t_name_length);
                    rightStrip(t_next_name, t_next_name_length);
                }

                rightStrip(cigar, cigar_length);
                rightStrip(sequence, sequence_length);
                rightStrip(quality, quality_length);

                if (q_name_length == 0 || t_name_length == 0 ||
                    cigar_length == 0 || t_next_name_length == 0 ||
                    sequence_length == 0 || quality_length == 0 ||
                    (sequence_length > 1 && quality_length > 1 &&
                    sequence_length != quality_length)) {

                    throw std::invalid_argument("[bioparser::SamParser] error: "
                        "invalid file format!");
                }

                dst.emplace_back(std::unique_ptr<T>(new T(q_name, q_name_length,
                    flag, t_name, t_name_length, t_begin, mapping_quality,
                    cigar, cigar_length, t_next_name, t_next_name_length,
                    t_next_begin, template_length, sequence, sequence_length,
                    quality, quality_length)));

                ++num_objects;
                current_bytes = 0;
                line_length = 0;
            } else {
                line[line_length++] = c;
                if (line_length == this->storage_.size()) {
                    this->storage_.resize(5 * kSSS + 2 * kLSS);
                    line = &(this->storage_[0]);
                }
            }
        }
    }

    return status;
}


}
