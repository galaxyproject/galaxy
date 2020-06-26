/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#pragma once

#include <string>
#include <vector>
#include <sstream>
#include <fstream>
#include <cassert>

namespace claragenomics
{

namespace cudapoa
{

/// \brief Parses window data file
///
/// \param[out] windows Reference to vector into which parsed window
///                     data is saved
/// \param[in] filename Name of file with window data
/// \param[in] total_windows Limit windows read to total windows, or
///                          loop over existing windows to fill remaining spots.
///                          -1 ignored the total_windows arg and uses all windows in the file.
inline void parse_window_data_file(std::vector<std::vector<std::string>>& windows, const std::string& filename, int32_t total_windows)
{
    std::ifstream infile(filename);
    if (!infile.good())
    {
        throw std::runtime_error("Cannot read file " + filename);
    }
    std::string line;
    int32_t num_sequences = 0;
    while (std::getline(infile, line))
    {
        if (num_sequences == 0)
        {
            std::istringstream iss(line);
            iss >> num_sequences;
            windows.emplace_back(std::vector<std::string>());
        }
        else
        {
            windows.back().push_back(line);
            num_sequences--;
        }
    }

    if (total_windows >= 0)
    {
        if (windows.size() > total_windows)
        {
            windows.erase(windows.begin() + total_windows, windows.end());
        }
        else if (windows.size() < total_windows)
        {
            int32_t windows_read = windows.size();
            while (windows.size() != total_windows)
            {
                windows.push_back(windows[windows.size() - windows_read]);
            }
        }

        assert(windows.size() == total_windows);
    }
}

/// \brief Parses golden value file with genome
///
/// \param[in] filename Name of file with reference genome
///
/// \return Genome string
inline std::string parse_golden_value_file(const std::string& filename)
{
    std::ifstream infile(filename);
    if (!infile.good())
    {
        throw std::runtime_error("Cannot read file " + filename);
    }

    std::string line;
    std::getline(infile, line);
    return line;
}
} // namespace cudapoa
} // namespace claragenomics
