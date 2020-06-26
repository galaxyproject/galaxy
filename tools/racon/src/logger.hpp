/*!
 * @file logger.hpp
 *
 * @brief Logger header file
 */

#pragma once

#include <cstdint>
#include <chrono>
#include <string>

namespace racon {

static const std::string version = "v1.0.0";

class Logger {
public:
    Logger();

    Logger(const Logger&) = default;
    Logger& operator=(const Logger&) = default;

    Logger(Logger&&) = default;
    Logger& operator=(Logger&&) = default;

    ~Logger();

    /*!
     * @brief Resets the time point
     */
    void log();

    /*!
     * @brief Prints the elapsed time from last time point to stderr
     */
    void log(const std::string& msg) const;

    /*!
     * @brief Prints a progress bar and the elapsed time from last time to
     * stderr (the progress bar resets after 20 calls)
     */
    void bar(const std::string& msg);

    /*!
     * @brief Prints the total elapsed time from the first log() call
     */
    void total(const std::string& msg) const;

private:
    double time_;
    std::uint32_t bar_;
    std::chrono::time_point<std::chrono::steady_clock> time_point_;
};

}
