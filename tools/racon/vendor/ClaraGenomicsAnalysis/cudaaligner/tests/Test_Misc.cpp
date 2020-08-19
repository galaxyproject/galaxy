/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include <claragenomics/utils/mathutils.hpp>

#include "gtest/gtest.h"

namespace claragenomics
{

namespace cudaaligner
{

TEST(TestCudaAlignerMisc, CeilingDivide)
{
    EXPECT_EQ(ceiling_divide(0, 5), 0);
    EXPECT_EQ(ceiling_divide(5, 5), 1);
    EXPECT_EQ(ceiling_divide(10, 5), 2);
    EXPECT_EQ(ceiling_divide(20, 5), 4);

    EXPECT_EQ(ceiling_divide(6, 5), 2);
    EXPECT_EQ(ceiling_divide(4, 5), 1);
}

} // namespace cudaaligner
} // namespace claragenomics
