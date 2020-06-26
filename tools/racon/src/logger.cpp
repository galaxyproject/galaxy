/*!
 * @file logger.cpp
 *
 * @brief Logger source file
 */

#include <iostream>

#include "logger.hpp"

namespace racon {

Logger::Logger()
        : time_(0.), bar_(0), time_point_() {
}

Logger::~Logger() {
}

void Logger::log() {
    auto now = std::chrono::steady_clock::now();
    if (time_point_ != std::chrono::time_point<std::chrono::steady_clock>()) {
        time_ += std::chrono::duration_cast<std::chrono::duration<double>>(now - time_point_).count();
    }
    time_point_ = now;
}

void Logger::log(const std::string& msg) const {
    std::cerr << msg << " " << std::fixed
        << std::chrono::duration_cast<std::chrono::duration<double>>(std::chrono::steady_clock::now() - time_point_).count()
        << " s" << std::endl;
}

void Logger::bar(const std::string& msg) {
    ++bar_;
    std::string progress_bar = "[" + std::string(bar_, '=') + (bar_ == 20 ? "" : ">" + std::string(19 - bar_, ' ')) + "]";

    std::cerr << msg << " " << progress_bar << " " << std::fixed
        << std::chrono::duration_cast<std::chrono::duration<double>>(std::chrono::steady_clock::now() - time_point_).count()
        << " s";

    bar_ %= 20;
    if (bar_ == 0) {
        std::cerr << std::endl;
    } else {
        std::cerr << "\r";
    }
}

void Logger::total(const std::string& msg) const {
    std::cerr << msg << " " << std::fixed
        << time_ + std::chrono::duration_cast<std::chrono::duration<double>>(std::chrono::steady_clock::now() - time_point_).count()
        << " s" << std::endl;
}

}
