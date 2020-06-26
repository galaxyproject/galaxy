/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include <claragenomics/logging/logging.hpp>

#include <spdlog/sinks/basic_file_sink.h>
#include <spdlog/sinks/stdout_sinks.h>

namespace claragenomics
{
namespace logging
{
static std::shared_ptr<spdlog::logger> logger = nullptr;

LoggingStatus Init(const char* filename)
{
    // for now, first call wins:
    if (logger != nullptr)
        return LoggingStatus::success;

    if (filename != nullptr)
    {
        try
        {
            logger = spdlog::basic_logger_mt("CGALogger", filename);
        }
        catch (const spdlog::spdlog_ex& ex)
        {
            return LoggingStatus::cannot_open_file;
        }
    }
    else
    {
        try
        {
            logger = spdlog::stderr_logger_mt("CGALogger");
        }
        catch (const spdlog::spdlog_ex& ex)
        {
            return LoggingStatus::cannot_open_stdout;
        }
    }

    spdlog::set_default_logger(logger);

#ifdef _DEBUG
    SetHeader(true, true);
#else
    SetHeader(false, false);
#endif

    spdlog::flush_every(std::chrono::seconds(1));

    return LoggingStatus::success;
}

LoggingStatus SetHeader(bool logTime, bool logLocation)
{
    std::string pattern = "";

    if (logTime)
        pattern = pattern + "[%H:%M:%S %z]";

    if (logLocation)
        pattern = pattern + "[%@]";

    pattern = pattern + "%v";

    spdlog::set_pattern(pattern);

    return LoggingStatus::success;
}
} // namespace logging
} // namespace claragenomics
