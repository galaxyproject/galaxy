#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

"""Classes for tool wrappers"""
import logging
import os
import shutil
import subprocess


class RaconWrapper:
    """Wrapper class for Racon with GPU support"""

    def __init__(self, tool_path=None, gpu=False):
        """Inits RaconWrapper with tool directory and GPU flag.

        Args:
            tool_path (string): Path where the racon tool (i.e. racon-gpu) is located
            gpu (boolean): Indicating using GPU-based Racon or CPU-based Racon
        """
        self.gpu = gpu
        if tool_path is None:
            self.racon_binary_path = "racon"
        else:
            self.racon_binary_path = tool_path

    def polish(self, reads_filepath, aligned_filepath, assembly_filepath,
               polished_filepath, extra_args="-m 8 -x -6 -g -8 -w 500 -t 12 -q -1"):
        """Polishes with Racon.

        Args:
            reads_filepath (string): Path where the reads are located
            aligned_filepath (string): Path where the aligned reads are located
            assembly_filepath (string): Path where the assembled sequence is located
            polished_filepath (string): Path for the output polished sequence
            extra_args (string): Extra settings for Racon, e.g. scores, number of threads
        """
        logging.info("Polish with racon:")
        if os.path.isfile(polished_filepath):
            logging.info("Overwriting existing file.")
            os.remove(polished_filepath)
        if self.gpu:
            cmd = "{} -c4 {} {} {} {} > {}".format(self.racon_binary_path,
                                                   extra_args,
                                                   reads_filepath,
                                                   aligned_filepath,
                                                   assembly_filepath,
                                                   polished_filepath)
        else:
            cmd = "{} {} {} {} {} > {}".format(
                self.racon_binary_path,
                extra_args,
                reads_filepath,
                aligned_filepath,
                assembly_filepath,
                polished_filepath)
        logging.info(cmd)
        subprocess.call(cmd, shell=True)


class Minimap2Wrapper:
    """Wrapper class for minimap2 tool"""

    def __init__(self, tool_path=None):
        """Inits Minimap2Wrapper with tool directory.

        Args:
            tool_path (string): Path where the minimap2 tool is located
        """
        if tool_path is None:
            self.minimap2_binary_path = "minimap2"
        else:
            self.minimap2_binary_path = tool_path

    def overlap(self, refs_filepath, reads_filepath, overlaps_filepath, args="", extra_args=""):
        """Creates overlaps with minimap2 tool for alignment.

        Args:
            refs_filepath (string): Path where the reference is located
            reads_filepath (string): Path where the reads are located
            overlaps_filepath (string): Path for the output alignments
            args (string): Parameters for different data types, e.g. -x ava-one
            extra_args (string): Extra settings e.g. number of threads
        """

        logging.info("Generate overlaps")
        if os.path.isfile(overlaps_filepath):
            logging.info("Overwriting existing file.")
            os.remove(overlaps_filepath)
        cmd = "{} {} {} {} {} > {}".format(
            self.minimap2_binary_path,
            args,
            refs_filepath,
            reads_filepath,
            extra_args,
            overlaps_filepath)
        logging.info(cmd)
        subprocess.call(cmd, shell=True)


class MiniasmWrapper:
    """Wrapper class for miniasm tool"""

    def __init__(self, tool_path=None):
        """Inits MiniasmWrapper with tool directory.

        Args:
            tool_path (string): Path where the miniasm tool is located
        """
        if tool_path is None:
            self.miniasm_binary_path = "miniasm"
        else:
            self.miniasm_binary_path = tool_path

    def assemble(self, reads_filepath, overlaps_filepath, assembly_filepath):
        """Assembles from reads and alignments.

        Args:
            reads_filepath (string): Path where the reads located
            overlaps_filepath (string): Path where the alignments are located
            assembly_filepath (string): Location for output assembly

        """
        logging.info("Assemble overlaps:")
        if os.path.isfile(assembly_filepath):
            logging.info("Overwriting existing file.")
            os.remove(assembly_filepath)
        cmd = "{} -f {} {} > {}".format(self.miniasm_binary_path, reads_filepath, overlaps_filepath, assembly_filepath)
        logging.info(cmd)
        subprocess.call(cmd, shell=True)


class QuastWrapper:
    """Wrapper class for Quast"""

    def __init__(self):
        pass

    def assess(self, assembly_filepath, reference_filepath, output_dir):
        """Assesses assembly compared to reference.

        Args:
            assembly_filepath (string): Path where the assembly is located
            reference_filepath (string): Path where the reference is located
            output_dir (string): Location for output files including report

        """
        if os.path.exists(output_dir):
            logging.info("Overwriting existing output folder.")
            shutil.rmtree(output_dir)
        logging.info("Generate report by quast:")
        cmd = "quast.py {} -r {} -o {}".format(assembly_filepath, reference_filepath, output_dir)
        subprocess.call(cmd, shell=True)
