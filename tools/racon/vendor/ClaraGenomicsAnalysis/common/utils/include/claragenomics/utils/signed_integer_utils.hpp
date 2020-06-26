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

#include <limits>
#include <cassert>
#include <stdexcept>
#include <type_traits>

namespace claragenomics
{

template <class Container>
typename std::make_signed<typename Container::size_type>::type get_size(Container const& c)
{
    using size_type   = typename Container::size_type;
    using signed_type = typename std::make_signed<size_type>::type;
    assert(c.size() <= static_cast<size_type>(std::numeric_limits<signed_type>::max()));
    return static_cast<signed_type>(c.size());
}

template <class T>
T throw_on_negative(T x, const char* message)
{
    static_assert(std::is_arithmetic<T>::value, "throw_on_negative expects an arithmetic type.");
    if (x < T(0))
        throw std::invalid_argument(message);
    return x;
}

} // namespace claragenomics
