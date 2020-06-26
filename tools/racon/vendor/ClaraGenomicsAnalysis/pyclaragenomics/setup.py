#!/usr/bin/env python3

#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import glob
import os
import shutil
from setuptools import setup, find_packages, Extension

from Cython.Build import cythonize


def get_verified_absolute_path(path):
    installed_path = os.path.abspath(path)
    if not os.path.exists(installed_path):
        raise RuntimeError("No valid path for requested component exists")
    return installed_path


def get_installation_requirments(file_path):
    with open(file_path, 'r') as file:
        requirements_file_content = \
            [line.strip() for line in file if line.strip() and not line.lstrip().startswith('#')]
    return requirements_file_content


def copy_all_files_in_directory(src, dest, file_ext="*.so"):
    files_to_copy = glob.glob(os.path.join(src, file_ext))
    if not files_to_copy:
        raise RuntimeError("No {} files under {}".format(src, file_ext))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        for file in files_to_copy:
            shutil.copy(file, dest)
            print("{} was copied into {}".format(file, dest))
    except (shutil.Error, PermissionError) as err:
        print('Could not copy {}. Error: {}'.format(file, err))
        raise err


# Must be set before calling pip
try:
    cga_install_dir = os.environ['CGA_INSTALL_DIR']
except KeyError as e:
    raise EnvironmentError(
        'CGA_INSTALL_DIR environment variables must be set').with_traceback(e.__traceback__)

# Get current dir (pyclaragenomics folder is copied into a temp directory created by pip)
current_dir = os.path.dirname(os.path.realpath(__file__))


# Copies shared libraries into clargenomics package
copy_all_files_in_directory(
    get_verified_absolute_path(os.path.join(cga_install_dir, "lib")),
    os.path.join(current_dir, "claragenomics/shared_libs/"),
)

# Classifiers for PyPI
pycga_classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9"
]

extensions = [
    Extension(
        "*",
        sources=[os.path.join("claragenomics/**/*.pyx")],
        include_dirs=[
            "/usr/local/cuda/include",
            get_verified_absolute_path(os.path.join(cga_install_dir, "include")),
        ],
        library_dirs=["/usr/local/cuda/lib64", get_verified_absolute_path(os.path.join(cga_install_dir, "lib"))],
        runtime_library_dirs=["/usr/local/cuda/lib64", os.path.join('$ORIGIN', os.pardir, 'shared_libs')],
        libraries=["cudapoa", "cudaaligner", "cudart", "logging"],
        language="c++",
        extra_compile_args=["-std=c++14"],
    )
]

setup(name='pyclaragenomics',
      version='0.4.3',
      description='NVIDIA genomics python libraries and utiliites',
      author='NVIDIA Corporation',
      url="https://github.com/clara-genomics/ClaraGenomicsAnalysis",
      include_package_data=True,
      data_files=[
          ('cga_shared_objects', glob.glob('claragenomics/shared_libs/*.so'))
      ],
      install_requires=get_installation_requirments(
          get_verified_absolute_path(os.path.join(current_dir, 'requirements.txt'))
      ),
      packages=find_packages(where=current_dir),
      python_requires='>=3.5',
      license='Apache License 2.0',
      long_description='Python libraries and utilities for manipulating genomics data',
      classifiers=pycga_classifiers,
      platforms=['any'],
      ext_modules=cythonize(extensions, compiler_directives={'embedsignature': True}),
      scripts=[os.path.join('bin', 'genome_simulator'),
               os.path.join('bin', 'assembly_evaluator')],
      )
