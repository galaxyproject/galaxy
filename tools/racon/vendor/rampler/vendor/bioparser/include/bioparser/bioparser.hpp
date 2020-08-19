/*!
 * @file bioparser.hpp
 *
 * @brief Bioparser header file
 */

#pragma once

#include <cstdint>
#include <cstring>
#include <exception>
#include <memory>
#include <string>
#include <vector>

#include "zlib.h"

namespace bioparser {

static const std::string version = "v2.1.1";

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
    std::uint32_t buffer_ptr_;
    std::uint32_t buffer_bytes_;
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
        : input_file_(input_file, gzclose), buffer_(65536, 0),
        buffer_ptr_(0), buffer_bytes_(0), storage_(storage_size, 0) {
}

template<class T>
inline Parser<T>::~Parser() {
}

template<class T>
inline void Parser<T>::reset() {
    gzseek(input_file_.get(), 0, SEEK_SET);
    buffer_ptr_ = 0;
    buffer_bytes_ = 0;
}

template<class T>
inline bool Parser<T>::parse(std::vector<std::shared_ptr<T>>& dst,
    std::uint64_t max_bytes, bool trim) {

    std::vector<std::unique_ptr<T>> tmp;
    auto ret = parse_objects(tmp, max_bytes, trim);

    dst.reserve(dst.size() + tmp.size());
    for (auto& it: tmp) {
        dst.emplace_back(std::move(it));
    }
    return ret;
}

template<class T>
inline FastaParser<T>::FastaParser(gzFile input_file)
        : Parser<T>(input_file, 4194304) {
}

template<class T>
inline FastaParser<T>::~FastaParser() {
}

template<class T>
inline bool FastaParser<T>::parse(std::vector<std::unique_ptr<T>>& dst,
    std::uint64_t max_bytes, bool trim) {

    auto input_file = this->input_file_.get();
    bool is_eof = false;

    std::uint64_t total_bytes = 0;
    std::uint32_t line_num = 0;
    std::uint32_t storage_ptr = 0;
    std::uint32_t data_ptr = 0;

    auto create_T = [&] () -> void {

        if (data_ptr == 0) {
            throw std::invalid_argument("[bioparser::FastaParser] error: "
                "invalid file format!");
        }

        std::uint32_t name_len = data_ptr;
        if (trim) {
            rightStripHard(&(this->storage_[0]), name_len);
        } else {
            rightStrip(&(this->storage_[0]), name_len);
        }
        std::uint32_t data_len = storage_ptr - data_ptr;
        rightStrip(&(this->storage_[data_ptr]), data_len);

        if (name_len == 0 || this->storage_[0] != '>' || data_len == 0) {
            throw std::invalid_argument("[bioparser::FastaParser] error: "
                "invalid file format!");
        }

        dst.emplace_back(std::unique_ptr<T>(new T(
            (const char*) &(this->storage_[1]), name_len - 1,
            (const char*) &(this->storage_[data_ptr]), data_len)));

        total_bytes += storage_ptr;
        storage_ptr = 0;
        data_ptr = 0;
    };

    while (true) {

        std::uint32_t begin_ptr = this->buffer_ptr_;
        for (; this->buffer_ptr_ < this->buffer_bytes_; ++this->buffer_ptr_) {
            auto c = this->buffer_[this->buffer_ptr_];
            if (c == '\n') {
                std::memcpy(&this->storage_[storage_ptr],
                    &this->buffer_[begin_ptr],
                    this->buffer_ptr_ - begin_ptr);
                storage_ptr += this->buffer_ptr_ - begin_ptr;
                begin_ptr = this->buffer_ptr_ + 1;
                if (line_num == 0) {
                    data_ptr = storage_ptr;
                    line_num = 1;
                }
            } else if (line_num == 1 && c == '>') {
                line_num = 0;
                create_T();
                if (total_bytes >= max_bytes) {
                    return true;
                }
            }
        }
        if (begin_ptr < this->buffer_ptr_) {
            std::memcpy(&this->storage_[storage_ptr],
                &this->buffer_[begin_ptr],
                this->buffer_ptr_ - begin_ptr);
            storage_ptr += this->buffer_ptr_ - begin_ptr;
        }
        this->buffer_ptr_ = 0;

        if (is_eof) {
            break;
        }

        this->buffer_bytes_ = gzread(input_file, this->buffer_.data(),
            this->buffer_.size());
        is_eof = this->buffer_bytes_ < this->buffer_.size();

        if (storage_ptr + this->buffer_bytes_ > this->storage_.size()) {
            this->storage_.resize(this->storage_.size() * 2);
        }
    }

    if (storage_ptr != 0) {
        create_T();
    }

    return false;
}

template<class T>
inline FastqParser<T>::FastqParser(gzFile input_file)
        : Parser<T>(input_file, 4194304) {
}

template<class T>
inline FastqParser<T>::~FastqParser() {
}

template<class T>
inline bool FastqParser<T>::parse(std::vector<std::unique_ptr<T>>& dst,
    std::uint64_t max_bytes, bool trim) {

    auto input_file = this->input_file_.get();
    bool is_eof = false;

    std::uint64_t total_bytes = 0;
    std::uint32_t line_num = 0;
    std::uint32_t storage_ptr = 0;
    std::uint32_t data_ptr = 0;
    std::uint32_t comm_ptr = 0;
    std::uint32_t qual_ptr = 0;

    auto create_T = [&] () -> void {

        if (data_ptr == 0 || comm_ptr == 0 || qual_ptr == 0) {
            throw std::invalid_argument("[bioparser::FastqParser] error: "
                "invalid file format!");
        }

        std::uint32_t name_len = data_ptr;
        if (trim) {
            rightStripHard(&(this->storage_[0]), name_len);
        } else {
            rightStrip(&(this->storage_[0]), name_len);
        }
        std::uint32_t data_len = comm_ptr - data_ptr;
        rightStrip(&(this->storage_[data_ptr]), data_len);
        std::uint32_t qual_len = storage_ptr - qual_ptr;
        rightStrip(&(this->storage_[qual_ptr]), qual_len);

        if (name_len == 0 || this->storage_[0] != '@' || data_len == 0 ||
            qual_len == 0 || data_len != qual_len) {
            throw std::invalid_argument("[bioparser::FastqParser] error: "
                "invalid file format!");
        }

        dst.emplace_back(std::unique_ptr<T>(new T(
            (const char*) &(this->storage_[1]), name_len - 1,
            (const char*) &(this->storage_[data_ptr]), data_len,
            (const char*) &(this->storage_[qual_ptr]), qual_len)));

        total_bytes += storage_ptr;
        storage_ptr = 0;
        data_ptr = 0;
        comm_ptr = 0;
        qual_ptr = 0;
    };

    while (true) {

        std::uint32_t begin_ptr = this->buffer_ptr_;
        for (; this->buffer_ptr_ < this->buffer_bytes_; ++this->buffer_ptr_) {
            auto c = this->buffer_[this->buffer_ptr_];
            if (c == '\n') {
                std::memcpy(&(this->storage_[storage_ptr]),
                    &(this->buffer_)[begin_ptr],
                    this->buffer_ptr_ - begin_ptr);
                storage_ptr += this->buffer_ptr_ - begin_ptr;
                begin_ptr = this->buffer_ptr_ + 1;
                if (line_num == 0) {
                    data_ptr = storage_ptr;
                    line_num = 1;
                } else if (line_num == 2) {
                    qual_ptr = storage_ptr;
                    line_num = 3;
                } else if (line_num == 3 && storage_ptr - qual_ptr == comm_ptr - data_ptr) {
                    line_num = 0;
                    create_T();
                    if (total_bytes >= max_bytes) {
                        ++this->buffer_ptr_;
                        return true;
                    }
                }
            } else if (line_num == 1 && c == '+') {
                comm_ptr = storage_ptr;
                line_num = 2;
            }
        }
        if (begin_ptr < this->buffer_ptr_) {
            std::memcpy(&(this->storage_[storage_ptr]),
                &(this->buffer_[begin_ptr]),
                this->buffer_ptr_ - begin_ptr);
            storage_ptr += this->buffer_ptr_ - begin_ptr;
        }
        this->buffer_ptr_ = 0;

        if (is_eof) {
            break;
        }

        this->buffer_bytes_ = gzread(input_file, this->buffer_.data(),
            this->buffer_.size());
        is_eof = this->buffer_bytes_ < this->buffer_.size();

        if (storage_ptr + this->buffer_bytes_ > this->storage_.size()) {
            this->storage_.resize(this->storage_.size() * 2);
        }
    }

    if (storage_ptr != 0) {
        create_T();
    }

    return false;
}

template<class T>
inline MhapParser<T>::MhapParser(gzFile input_file)
        : Parser<T>(input_file, 65536) {
}

template<class T>
inline MhapParser<T>::~MhapParser() {
}

template<class T>
inline bool MhapParser<T>::parse(std::vector<std::unique_ptr<T>>& dst,
    std::uint64_t max_bytes, bool) {

    auto input_file = this->input_file_.get();
    bool is_eof = false;

    std::uint64_t total_bytes = 0;
    std::uint32_t storage_ptr = 0;

    std::uint64_t a_id = 0, b_id = 0;
    std::uint32_t a_rc = 0, a_begin = 0, a_end = 0, a_length = 0, b_rc = 0,
        b_begin = 0, b_end = 0, b_length = 0, minmers = 0;
    double error = 0;

    auto create_T = [&] () -> void {
        this->storage_[storage_ptr] = 0;
        rightStrip(&(this->storage_[0]), storage_ptr);

        std::uint32_t num_values = 0, begin = 0;
        while (true) {
            std::uint32_t end = begin;
            for (std::uint32_t j = begin; j < storage_ptr; ++j) {
                if (this->storage_[j] == ' ') {
                    end = j;
                    break;
                }
            }
            if (end == begin) {
                end = storage_ptr;
            }
            this->storage_[end] = 0;

            switch (num_values) {
                case 0: a_id = atoll(&(this->storage_[begin])); break;
                case 1: b_id = atoll(&(this->storage_[begin])); break;
                case 2: error = atof(&(this->storage_[begin])); break;
                case 3: minmers = atoi(&(this->storage_[begin])); break;
                case 4: a_rc = atoi(&(this->storage_[begin])); break;
                case 5: a_begin = atoi(&(this->storage_[begin])); break;
                case 6: a_end = atoi(&(this->storage_[begin])); break;
                case 7: a_length = atoi(&(this->storage_[begin])); break;
                case 8: b_rc = atoi(&(this->storage_[begin])); break;
                case 9: b_begin = atoi(&(this->storage_[begin])); break;
                case 10: b_end = atoi(&(this->storage_[begin])); break;
                case 11: b_length = atoi(&(this->storage_[begin])); break;
                default: break;
            }
            num_values++;
            if (end == storage_ptr || num_values == 12) {
                break;
            }
            begin = end + 1;
        }

        if (num_values != 12) {
            throw std::invalid_argument("[bioparser::MhapParser] error: "
                "invalid file format!");
        }

        dst.emplace_back(std::unique_ptr<T>(new T(a_id, b_id, error,
            minmers, a_rc, a_begin, a_end, a_length, b_rc, b_begin,
            b_end, b_length)));

        total_bytes += storage_ptr;
        storage_ptr = 0;
    };

    while (true) {

        std::uint32_t begin_ptr = this->buffer_ptr_;
        for (; this->buffer_ptr_ < this->buffer_bytes_; ++this->buffer_ptr_) {
            auto c = this->buffer_[this->buffer_ptr_];
            if (c == '\n') {
                std::memcpy(&this->storage_[storage_ptr],
                    &this->buffer_[begin_ptr],
                    this->buffer_ptr_ - begin_ptr);
                storage_ptr += this->buffer_ptr_ - begin_ptr;
                begin_ptr = this->buffer_ptr_ + 1;
                create_T();
                if (total_bytes >= max_bytes) {
                    ++this->buffer_ptr_;
                    return true;
                }
            }
        }
        if (begin_ptr < this->buffer_ptr_) {
            std::memcpy(&this->storage_[storage_ptr],
                &this->buffer_[begin_ptr],
                this->buffer_ptr_ - begin_ptr);
            storage_ptr += this->buffer_ptr_ - begin_ptr;
        }
        this->buffer_ptr_ = 0;

        if (is_eof) {
            break;
        }

        this->buffer_bytes_ = gzread(input_file, this->buffer_.data(),
            this->buffer_.size());
        is_eof = this->buffer_bytes_ < this->buffer_.size();

        if (storage_ptr + this->buffer_bytes_ > this->storage_.size()) {
            this->storage_.resize(this->storage_.size() * 2);
        }
    }

    if (storage_ptr != 0) {
        create_T();
    }

    return false;
}

template<class T>
inline PafParser<T>::PafParser(gzFile input_file)
        : Parser<T>(input_file, 65536) {
}

template<class T>
inline PafParser<T>::~PafParser() {
}

template<class T>
inline bool PafParser<T>::parse(std::vector<std::unique_ptr<T>>& dst,
    std::uint64_t max_bytes, bool trim) {

    auto input_file = this->input_file_.get();
    bool is_eof = false;

    std::uint64_t total_bytes = 0;
    std::uint32_t storage_ptr = 0;

    const char* q_name = nullptr, * t_name = nullptr;
    std::uint32_t q_name_length = 0, q_length = 0, q_begin = 0, q_end = 0,
        t_name_length = 0, t_length = 0, t_begin = 0, t_end = 0,
        matching_bases = 0, overlap_length = 0, mapping_quality = 0;
    char orientation = '\0';

    auto create_T = [&] () -> void {
        this->storage_[storage_ptr] = 0;
        rightStrip(&(this->storage_[0]), storage_ptr);

        std::uint32_t num_values = 0, begin = 0;
        while (true) {
            std::uint32_t end = begin;
            for (std::uint32_t j = begin; j < storage_ptr; ++j) {
                if (this->storage_[j] == '\t') {
                    end = j;
                    break;
                }
            }
            if (end == begin) {
                end = storage_ptr;
            }
            this->storage_[end] = 0;

            switch (num_values) {
                case 0:
                    q_name = &(this->storage_[begin]);
                    q_name_length = end - begin;
                    break;
                case 1: q_length = atoi(&(this->storage_[begin])); break;
                case 2: q_begin = atoi(&(this->storage_[begin])); break;
                case 3: q_end = atoi(&(this->storage_[begin])); break;
                case 4: orientation = this->storage_[begin]; break;
                case 5:
                    t_name = &(this->storage_[begin]);
                    t_name_length = end - begin;
                    break;
                case 6: t_length = atoi(&(this->storage_[begin])); break;
                case 7: t_begin = atoi(&(this->storage_[begin])); break;
                case 8: t_end = atoi(&(this->storage_[begin])); break;
                case 9: matching_bases = atoi(&(this->storage_[begin])); break;
                case 10: overlap_length = atoi(&(this->storage_[begin])); break;
                case 11: mapping_quality = atoi(&(this->storage_[begin])); break;
                default: break;
            }
            num_values++;
            if (end == storage_ptr || num_values == 12) {
                break;
            }
            begin = end + 1;
        }

        if (num_values != 12) {
            throw std::invalid_argument("[bioparser::PafParser] error: "
                "invalid file format!");
        }

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

        total_bytes += storage_ptr;
        storage_ptr = 0;
    };

    while (true) {

        std::uint32_t begin_ptr = this->buffer_ptr_;
        for (; this->buffer_ptr_ < this->buffer_bytes_; ++this->buffer_ptr_) {
            auto c = this->buffer_[this->buffer_ptr_];
            if (c == '\n') {
                std::memcpy(&this->storage_[storage_ptr],
                    &this->buffer_[begin_ptr],
                    this->buffer_ptr_ - begin_ptr);
                storage_ptr += this->buffer_ptr_ - begin_ptr;
                begin_ptr = this->buffer_ptr_ + 1;
                create_T();
                if (total_bytes >= max_bytes) {
                    ++this->buffer_ptr_;
                    return true;
                }
            }
        }
        if (begin_ptr < this->buffer_ptr_) {
            std::memcpy(&this->storage_[storage_ptr],
                &this->buffer_[begin_ptr],
                this->buffer_ptr_ - begin_ptr);
            storage_ptr += this->buffer_ptr_ - begin_ptr;
        }
        this->buffer_ptr_ = 0;

        if (is_eof) {
            break;
        }

        this->buffer_bytes_ = gzread(input_file, this->buffer_.data(),
            this->buffer_.size());
        is_eof = this->buffer_bytes_ < this->buffer_.size();

        if (storage_ptr + this->buffer_bytes_ > this->storage_.size()) {
            this->storage_.resize(this->storage_.size() * 2);
        }
    }

    if (storage_ptr != 0) {
        create_T();
    }

    return false;
}

template<class T>
inline SamParser<T>::SamParser(gzFile input_file)
        : Parser<T>(input_file, 65536) {
}

template<class T>
inline SamParser<T>::~SamParser() {
}

template<class T>
inline bool SamParser<T>::parse(std::vector<std::unique_ptr<T>>& dst,
    std::uint64_t max_bytes, bool trim) {

    auto input_file = this->input_file_.get();
    bool is_eof = false;

    std::uint64_t total_bytes = 0;
    std::uint32_t storage_ptr = 0;

    const char* q_name = nullptr, * t_name = nullptr, * cigar = nullptr,
        * t_next_name = nullptr, * sequence = nullptr, * quality = nullptr;
    std::uint32_t q_name_length = 0, flag = 0, t_name_length = 0, t_begin = 0,
        mapping_quality = 0, cigar_length = 0, t_next_name_length = 0,
        t_next_begin = 0, template_length = 0, sequence_length = 0,
        quality_length = 0;

    auto create_T = [&] () -> void {
        this->storage_[storage_ptr] = 0;
        rightStrip(&(this->storage_[0]), storage_ptr);

        std::uint32_t num_values = 0, begin = 0;
        while (true) {
            std::uint32_t end = begin;
            for (std::uint32_t j = begin; j < storage_ptr; ++j) {
                if (this->storage_[j] == '\t') {
                    end = j;
                    break;
                }
            }
            if (end == begin) {
                end = storage_ptr;
            }
            this->storage_[end] = 0;

            switch (num_values) {
                case 0:
                    q_name = &(this->storage_[begin]);
                    q_name_length = end - begin;
                    break;
                case 1: flag = atoi(&(this->storage_[begin])); break;
                case 2:
                    t_name = &(this->storage_[begin]);
                    t_name_length = end - begin;
                    break;
                case 3: t_begin = atoi(&(this->storage_[begin])); break;
                case 4: mapping_quality = atoi(&(this->storage_[begin])); break;
                case 5:
                    cigar = &(this->storage_[begin]);
                    cigar_length = end - begin;
                    break;
                case 6:
                    t_next_name = &(this->storage_[begin]);
                    t_next_name_length = end - begin;
                    break;
                case 7: t_next_begin = atoi(&(this->storage_[begin])); break;
                case 8: template_length = atoi(&(this->storage_[begin])); break;
                case 9:
                    sequence = &(this->storage_[begin]);
                    sequence_length = end - begin;
                    break;
                case 10:
                    quality = &(this->storage_[begin]);
                    quality_length = end - begin;
                    break;
                default: break;
            }
            num_values++;
            if (end == storage_ptr || num_values == 11) {
                break;
            }
            begin = end + 1;
        }

        if (num_values != 11) {
            throw std::invalid_argument("[bioparser::SamParser] error: "
                "invalid file format!");
        }

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

        total_bytes += storage_ptr;
        storage_ptr = 0;
    };

    while (true) {

        std::uint32_t begin_ptr = this->buffer_ptr_;
        for (; this->buffer_ptr_ < this->buffer_bytes_; ++this->buffer_ptr_) {
            auto c = this->buffer_[this->buffer_ptr_];
            if (c == '\n') {
                if (this->buffer_[begin_ptr] == '@') {
                    begin_ptr = this->buffer_ptr_ + 1;
                    storage_ptr = 0;
                    continue;
                }
                std::memcpy(&this->storage_[storage_ptr],
                    &this->buffer_[begin_ptr],
                    this->buffer_ptr_ - begin_ptr);
                storage_ptr += this->buffer_ptr_ - begin_ptr;
                begin_ptr = this->buffer_ptr_ + 1;
                create_T();
                if (total_bytes >= max_bytes) {
                    ++this->buffer_ptr_;
                    return true;
                }
            }
        }
        if (begin_ptr < this->buffer_ptr_) {
            std::memcpy(&this->storage_[storage_ptr],
                &this->buffer_[begin_ptr],
                this->buffer_ptr_ - begin_ptr);
            storage_ptr += this->buffer_ptr_ - begin_ptr;
        }
        this->buffer_ptr_ = 0;

        if (is_eof) {
            break;
        }

        this->buffer_bytes_ = gzread(input_file, this->buffer_.data(),
            this->buffer_.size());
        is_eof = this->buffer_bytes_ < this->buffer_.size();

        if (storage_ptr + this->buffer_bytes_ > this->storage_.size()) {
            this->storage_.resize(this->storage_.size() * 2);
        }
    }

    if (storage_ptr != 0) {
        create_T();
    }

    return false;
}

}
