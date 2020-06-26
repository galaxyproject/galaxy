#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

"""Class for utility functions"""
import logging
import os
import subprocess


class Utilities:
    """Class for small utility functions"""

    @staticmethod
    def gfa2fa(gfa_filepath, fa_filepath):
        """Converts GFA file format to FA file format.

        Args:
            gfa_filepath (string): Path where the GFA file is located
            fa_filepath (string): Location for output files including FA file

        """
        logging.info("Convert GFA to FA file:")
        if os.path.isfile(fa_filepath):
            logging.info("Overwriting existing file.")
            os.remove(fa_filepath)
        cmd = """awk '/^S/{{print ">"$2"\\n"$3}}' {} | fold > {}""".format(gfa_filepath, fa_filepath)
        logging.info(cmd)
        subprocess.call(cmd, shell=True)

    @staticmethod
    def calculate_error(report_filepath):
        """Calculates error rate from quast generated report (report.txt).

        Args:
            report_filepath (string): Path for the report.txt in quast output folder

        """
        lines = [line.rstrip('\n') for line in open(report_filepath)]
        mismatch = [i for i in lines if i.startswith('# mismatches')][0].split()
        indels = [i for i in lines if i.startswith('# indels')][0].split()
        error = (float(mismatch[-1]) + float(indels[-1])) / 10**5 * 100
        logging.info("The error rate is {}%".format(str(error)))
        return error
