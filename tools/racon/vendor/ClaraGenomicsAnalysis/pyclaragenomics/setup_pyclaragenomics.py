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

import argparse
import os
import subprocess


def parse_arguments():
    parser = argparse.ArgumentParser(description='build & install Clara Genomics Analysis SDK.')
    parser.add_argument('--build_output_folder',
                        required=False,
                        default="cga_build",
                        help="Choose an output folder for building")
    parser.add_argument('--create_wheel_only',
                        required=False,
                        action='store_true',
                        help="Creates a python wheel package from pyclaragenomics (no installation)")
    parser.add_argument('--develop',
                        required=False,
                        action='store_true',
                        help="Install using pip editble mode")
    return parser.parse_args()


class CMakeWrapper:
    """Class to encapsulate building a CMake project."""

    def __init__(self,
                 cmake_root_dir,
                 cmake_build_path="cmake_build",
                 cga_install_dir="cmake_build/install",
                 cmake_extra_args=""):
        """
        Class constructor.

        Args:
            cmake_root_dir : Root directory of CMake project
            cmake_build_path : cmake build output folder
            cga_install_dir: Clara Genomics Analysis installation directory
            cmake_extra_args : Extra string arguments to be passed to CMake during setup
        """
        self.cmake_root_dir = os.path.abspath(cmake_root_dir)
        self.build_path = os.path.abspath(cmake_build_path)
        self.cga_install_dir = os.path.abspath(cga_install_dir)
        self.cmake_extra_args = cmake_extra_args
        self.cuda_toolkit_root_dir = os.environ.get("CUDA_TOOLKIT_ROOT_DIR")

    def run_cmake_cmd(self):
        cmake_args = ['-DCMAKE_INSTALL_PREFIX=' + self.cga_install_dir,
                      '-DCMAKE_BUILD_TYPE=' + 'Release',
                      '-DCMAKE_INSTALL_RPATH=' + os.path.join(self.cga_install_dir, "lib")]
        cmake_args += [self.cmake_extra_args] if self.cmake_extra_args else []

        if self.cuda_toolkit_root_dir:
            cmake_args += ["-DCUDA_TOOLKIT_ROOT_DIR=%s" % self.cuda_toolkit_root_dir]

        if not os.path.exists(self.build_path):
            os.makedirs(self.build_path)

        subprocess.check_call(['cmake', self.cmake_root_dir] + cmake_args, cwd=self.build_path)

    def run_build_cmd(self):
        build_args = ['--', '-j16', 'install']
        subprocess.check_call(['cmake', '--build', '.'] + build_args, cwd=self.build_path)

    def build(self):
        self.run_cmake_cmd()
        self.run_build_cmd()


def setup_python_binding(is_develop_mode, wheel_output_folder, pycga_dir, cga_install_dir):
    if wheel_output_folder:
        setup_command = [
            'pip', 'wheel', '.',
            '--global-option', 'sdist',
            '--wheel-dir', wheel_output_folder, '--no-deps'
        ]
        completion_message = \
            "A wheel file was create for pyclaragenomics under {}".format(wheel_output_folder)
    else:
        setup_command = ['pip', 'install'] + (['-e'] if is_develop_mode else []) + ["."]
        completion_message = \
            "pyclaragenomics was successfully setup in {} mode!".format(
                "development" if args.develop else "installation")

    subprocess.check_call(setup_command,
                          env={
                              **os.environ,
                              'CGA_INSTALL_DIR': cga_install_dir
                          },
                          cwd=pycga_dir)
    print(completion_message)


if __name__ == "__main__":

    args = parse_arguments()
    current_dir = os.path.dirname(os.path.realpath(__file__))
    cga_installation_directory = os.path.join(args.build_output_folder, "install")
    # Build & install Clara Genomics Analysis SDK
    cmake_proj = CMakeWrapper(cmake_root_dir=os.path.dirname(current_dir),
                              cmake_build_path=args.build_output_folder,
                              cga_install_dir=cga_installation_directory,
                              cmake_extra_args="-Dcga_build_shared=ON")
    cmake_proj.build()
    # Setup pyclaragenomics
    setup_python_binding(
        is_develop_mode=args.develop,
        wheel_output_folder='pyclaragenomics_wheel/' if args.create_wheel_only else None,
        pycga_dir=current_dir,
        cga_install_dir=os.path.realpath(cga_installation_directory)
    )
