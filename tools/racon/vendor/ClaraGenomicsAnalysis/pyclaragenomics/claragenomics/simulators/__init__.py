#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

NUCLEOTIDES = set(('A', 'C', 'G', 'T'))

HIGH_GC_HOMOPOLYMERIC_TRANSITIONS = {
    "A": {
        "A": 0.25 * 3,
        "C": 0.25 * 1.25,
        "G": 0.25 * 1.25,
        "T": 0.25},
    "C": {
        "A": 0.25,
        "C": 0.25 * 3,
        "G": 0.25 * 1.25,
        "T": 0.25},
    "G": {
        "A": 0.25,
        "C": 0.25 * 1.25,
        "G": 0.25 * 1.25,
        "T": 0.25 * 3},
    "T": {
        "A": 0.25,
        "C": 0.25 * 3,
        "G": 0.25 * 3,
        "T": 0.25 * 1.25}}

HOMOGENOUS_TRANSITIONS = {
    "A": {
        "A": 0.25 * 10,
        "C": 0.25,
        "G": 0.25,
        "T": 0.25},
    "C": {
        "A": 0.25,
        "C": 0.25,
        "G": 0.25,
        "T": 0.25},
    "G": {
        "A": 0.25,
        "C": 0.25,
        "G": 0.25,
        "T": 0.25},
    "T": {
        "A": 0.25,
        "C": 0.25,
        "G": 0.25,
        "T": 0.25}}
