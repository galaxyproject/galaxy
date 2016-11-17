import logging
import os
import unittest

from testfixtures import log_capture

import galaxy.jobs.dynamic_tool_destination as dt
from galaxy.jobs.dynamic_tool_destination import map_tool_to_destination
from galaxy.jobs.mapper import JobMappingException

from . import mockGalaxy as mg
from . import ymltests as yt

theApp = mg.App( "waffles_default", "test_spec")
script_dir = os.path.dirname(__file__)

# ======================Jobs====================================
zeroJob = mg.Job()

emptyJob = mg.Job()
emptyJob.add_input_dataset( mg.InputDataset("input1", mg.Dataset( (script_dir + "/data/test.empty"), "txt", 14)) )

failJob = mg.Job()
failJob.add_input_dataset( mg.InputDataset("input1", mg.Dataset( (script_dir + "/data/test1.full"), "txt", 15)) )

msfileJob = mg.Job()
msfileJob.add_input_dataset( mg.InputDataset("input1", mg.Dataset( (script_dir + "/data/not_here.full"), "txt", 15)) )

notfileinpJob = mg.Job()
msfileJob.add_input_dataset( mg.InputDataset("input1", mg.NotAFile() ) )

runJob = mg.Job()
runJob.add_input_dataset( mg.InputDataset("input1", mg.Dataset( (script_dir + "/data/test3.full"), "txt", 15)) )

argJob = mg.Job()
argJob.add_input_dataset( mg.InputDataset("input1", mg.Dataset( (script_dir + "/data/test3.full"), "txt", 15)) )
argJob.set_arg_value( "careful", True )

argNotFoundJob = mg.Job()
argNotFoundJob.add_input_dataset( mg.InputDataset("input1", mg.Dataset( (script_dir + "/data/test3.full"), "txt", 15)) )
argNotFoundJob.set_arg_value( "careful", False )

dbJob = mg.Job()
dbJob.add_input_dataset( mg.InputDataset("input1", mg.Dataset( (script_dir + "/data/test.fasta"), "fasta", 10)) )

dbcountJob = mg.Job()
dbcountJob.add_input_dataset( mg.InputDataset("input1", mg.Dataset( (script_dir + "/data/test.fasta"), "fasta", None)) )

# ======================Tools===================================
vanillaTool = mg.Tool( 'test' )

unTool = mg.Tool( 'unregistered' )

overlapTool = mg.Tool( 'test_overlap' )

defaultTool = mg.Tool( 'test_tooldefault' )

dbTool = mg.Tool( 'test_db' )
dbinfTool = mg.Tool( 'test_db_high' )

argTool = mg.Tool( 'test_arguments' )

noVBTool = mg.Tool( 'test_no_verbose' )

usersTool = mg.Tool( 'test_users' )

numinputsTool = mg.Tool( 'test_num_input_datasets' )

# =======================YML file================================
path = script_dir + "/data/tool_destination.yml"
priority_path = script_dir + "/data/priority_tool_destination.yml"
broken_default_dest_path = script_dir + "/data/dest_fail.yml"
no_verbose_path = script_dir + "/data/test_no_verbose.yml"
users_test_path = script_dir + "/data/test_users.yml"
num_input_datasets_test_path = script_dir + "/data/test_num_input_datasets.yml"

# ======================Test Variables=========================
value = 1
valueK = value * 1024
valueM = valueK * 1024
valueG = valueM * 1024
valueT = valueG * 1024
valueP = valueT * 1024
valueE = valueP * 1024
valueZ = valueE * 1024
valueY = valueZ * 1024


class TestDynamicToolDestination(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.logger = logging.getLogger()

    # =======================map_tool_to_destination()================================

    @log_capture()
    def test_brokenDestYML(self, l):
        self.assertRaises(JobMappingException, map_tool_to_destination, runJob, theApp, vanillaTool, "user@email.com", True, broken_default_dest_path)

        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'No global default destination specified in config!'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Loading file: input1' + script_dir + '/data/test3.full'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Total size: 3.23 KB')
        )

    @log_capture()
    def test_filesize_empty(self, l):
        self.assertRaises(JobMappingException, map_tool_to_destination, emptyJob, theApp, vanillaTool, "user@email.com", True, path)
        self.assertRaises(JobMappingException, map_tool_to_destination, emptyJob, theApp, vanillaTool, "user@email.com", True, priority_path)

        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Loading file: input1' + script_dir + '/data/test.empty'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Total size: 0.00 B'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Total number of files: 1'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Loading file: input1' + script_dir + '/data/test.empty'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Total size: 0.00 B'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Total number of files: 1')
        )

    @log_capture()
    def test_filesize_zero(self, l):
        self.assertRaises(JobMappingException, map_tool_to_destination, zeroJob, theApp, vanillaTool, "user@email.com", True, path)
        self.assertRaises(JobMappingException, map_tool_to_destination, zeroJob, theApp, vanillaTool, "user@email.com", True, priority_path)

        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Total size: 0.00 B'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Total number of files: 0'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Total size: 0.00 B'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Total number of files: 0')
        )

    @log_capture()
    def test_filesize_fail(self, l):
        self.assertRaises(JobMappingException, map_tool_to_destination, failJob, theApp, vanillaTool, "user@email.com", True, path)
        self.assertRaises(JobMappingException, map_tool_to_destination, failJob, theApp, vanillaTool, "user@email.com", True, priority_path)

        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Loading file: input1' + script_dir + '/data/test1.full'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Total size: 293.00 B'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Total number of files: 1'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Loading file: input1' + script_dir + '/data/test1.full'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Total size: 293.00 B'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Total number of files: 1')
        )

    @log_capture()
    def test_filesize_run(self, l):
        job = map_tool_to_destination( runJob, theApp, vanillaTool, "user@email.com", True, path )
        self.assertEquals( job, 'Destination1' )
        priority_job = map_tool_to_destination( runJob, theApp, vanillaTool, "user@email.com", True, priority_path )
        self.assertEquals( priority_job, 'Destination1_high' )

        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Loading file: input1' + script_dir + '/data/test3.full'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Total size: 3.23 KB'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Total number of files: 1'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Running 'test' with 'Destination1'."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Loading file: input1' + script_dir + '/data/test3.full'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Total size: 3.23 KB'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Total number of files: 1'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Running 'test' with 'Destination1_high'.")
        )

    @log_capture()
    def test_default_tool(self, l):
        job = map_tool_to_destination( runJob, theApp, defaultTool, "user@email.com", True, path )
        self.assertEquals( job, 'waffles_default' )
        priority_job = map_tool_to_destination( runJob, theApp, defaultTool, "user@email.com", True, priority_path )
        self.assertEquals( priority_job, 'waffles_default_high' )

        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Tool 'test_tooldefault' not specified in config. Using default destination."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Running 'test_tooldefault' with 'waffles_default'."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Tool 'test_tooldefault' not specified in config. Using default destination."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Running 'test_tooldefault' with 'waffles_default_high'.")
        )

    @log_capture()
    def test_arguments_tool(self, l):
        job = map_tool_to_destination( argJob, theApp, argTool, "user@email.com", True, path )
        self.assertEquals( job, 'Destination6' )
        priority_job = map_tool_to_destination( argJob, theApp, argTool, "user@email.com", True, priority_path )
        self.assertEquals( priority_job, 'Destination6_med' )

        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Running 'test_arguments' with 'Destination6'."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Running 'test_arguments' with 'Destination6_med'.")
        )

    @log_capture()
    def test_arguments_arg_not_found(self, l):
        job = map_tool_to_destination( argNotFoundJob, theApp, argTool, "user@email.com", True, path )
        self.assertEquals( job, 'waffles_default' )
        priority_job = map_tool_to_destination( argNotFoundJob, theApp, argTool, "user@email.com", True, priority_path )
        self.assertEquals( priority_job, 'waffles_default_high' )

        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Running 'test_arguments' with 'waffles_default'."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Running 'test_arguments' with 'waffles_default_high'.")
        )

    @log_capture()
    def test_tool_not_found(self, l):
        job = map_tool_to_destination( runJob, theApp, unTool, "user@email.com", True, path )
        self.assertEquals( job, 'waffles_default' )
        priority_job = map_tool_to_destination( runJob, theApp, unTool, "user@email.com", True, priority_path )
        self.assertEquals( priority_job, 'waffles_default_high' )

        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Tool 'unregistered' not specified in config. Using default destination."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Running 'unregistered' with 'waffles_default'."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Tool 'unregistered' not specified in config. Using default destination."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Running 'unregistered' with 'waffles_default_high'.")
        )

    @log_capture()
    def test_fasta(self, l):
        job = map_tool_to_destination( dbJob, theApp, dbTool, "user@email.com", True, path )
        self.assertEquals( job, 'Destination4' )
        priority_job = map_tool_to_destination( dbJob, theApp, dbTool, "user@email.com", True, priority_path )
        self.assertEquals( priority_job, 'Destination4_high' )

        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Loading file: input1' + script_dir + '/data/test.fasta'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Total amount of records: 10'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Running 'test_db' with 'Destination4'."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Loading file: input1' + script_dir + '/data/test.fasta'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Total amount of records: 10'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Running 'test_db' with 'Destination4_high'.")
        )

    @log_capture()
    def test_fasta_count(self, l):
        job = map_tool_to_destination( dbcountJob, theApp, dbTool, "user@email.com", True, path )
        self.assertEquals( job, 'Destination4' )
        priority_job = map_tool_to_destination( dbcountJob, theApp, dbTool, "user@email.com", True, priority_path )
        self.assertEquals( priority_job, 'Destination4_high' )

        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Loading file: input1' + script_dir + '/data/test.fasta'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Total amount of records: 6'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Running 'test_db' with 'Destination4'."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Loading file: input1' + script_dir + '/data/test.fasta'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Total amount of records: 6'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Running 'test_db' with 'Destination4_high'.")
        )

    @log_capture()
    def test_no_verbose(self, l):
        job = map_tool_to_destination( runJob, theApp, noVBTool, "user@email.com", True, no_verbose_path )
        self.assertEquals( job, 'Destination1' )

        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Running 'test_no_verbose' with 'Destination1'.")
        )

    @log_capture()
    def test_authorized_user(self, l):
        job = map_tool_to_destination( runJob, theApp, usersTool, "user@email.com", True, users_test_path )
        self.assertEquals( job, 'special_cluster' )

        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Running 'test_users' with 'special_cluster'."),
        )

    @log_capture()
    def test_unauthorized_user(self, l):
        job = map_tool_to_destination( runJob, theApp, usersTool, "userblah@email.com", True, users_test_path )
        self.assertEquals( job, 'lame_cluster' )

        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Running 'test_users' with 'lame_cluster'.")
        )


# ================================Invalid yaml files==============================
    @log_capture()
    def test_no_file(self, l):
        self.assertRaises(IOError, dt.parse_yaml, path="")
        l.check()

    @log_capture()
    def test_bad_nice(self, l):
        dt.parse_yaml(path=yt.ivYMLTest11, test=True)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG',
             "Running config validation..."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG',
             "nice_value goes from -20 to 20; rule 1 in 'spades' has a nice_value of '-21'. Setting nice_value to 0."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_empty_file(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest2, test=True), {})

    @log_capture()
    def test_no_tool_name(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest3, test=True), yt.iv3dict)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Malformed YML; expected job name, but found a list instead!'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_no_rule_type(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest4, test=True), yt.ivDict)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "No rule_type found for rule 1 in 'spades'."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_no_rule_lower_bound(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest51, test=True), yt.ivDict)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Missing bounds for rule 1 in 'spades'. Ignoring rule."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_no_rule_upper_bound(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest52, test=True), yt.ivDict)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Missing bounds for rule 1 in 'spades'. Ignoring rule."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_no_rule_arg(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest53, test=True), yt.ivDict53)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Found a fail_message for rule 1 in 'spades', but destination is not 'fail'! Setting destination to 'fail'."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_bad_rule_type(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest6, test=True), yt.ivDict)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Unrecognized rule_type 'iencs' found in 'spades'. Ignoring..."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_no_err_msg(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest91, test=True), yt.iv91dict)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "No nice_value found for rule 1 in 'spades'. Setting nice_value to 0."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Missing a fail_message for rule 1 in 'spades'. Adding generic fail_message."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_no_default_dest(self, l):
        dt.parse_yaml(path=yt.ivYMLTest7, test=True)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'No global default destination specified in config!'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_invalid_category(self, l):
        dt.parse_yaml(path=yt.ivYMLTest8, test=True)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'No global default destination specified in config!'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Unrecognized category 'ice_cream' found in config file!"),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_arguments_no_err_msg(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest12, test=True), yt.iv12dict)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG',
            "Missing a fail_message for rule 1 in 'spades'. Adding generic fail_message."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_arguments_no_args(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest131, test=True), yt.iv131dict)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG',
            "No arguments found for rule 1 in 'spades' despite being of type arguments. Ignoring rule."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_arguments_no_arg(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest132, test=True), yt.iv132dict)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Found a fail_message for rule 1 in 'spades', but destination is not 'fail'! Setting destination to 'fail'."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_return_bool_for_multiple_jobs(self, l):
        self.assertFalse(dt.parse_yaml(path=yt.ivYMLTest133, test=True, return_bool=True))
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Missing a fail_message for rule 1 in 'smalt'.")
        )

    @log_capture()
    def test_return_rule_for_multiple_jobs(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest133, test=True), yt.iv133dict)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Missing a fail_message for rule 1 in 'smalt'. Adding generic fail_message."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_return_bool_for_no_destination(self, l):
        self.assertFalse(dt.parse_yaml(path=yt.ivYMLTest134, test=True, return_bool=True))
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "No destination specified for rule 1 in 'spades'.")
        )

    @log_capture()
    def test_return_rule_for_no_destination(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest134, test=True), yt.iv134dict)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "No destination specified for rule 1 in 'spades'. Ignoring..."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_return_rule_for_reversed_bounds(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest135, test=True), yt.iv135dict)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "lower_bound exceeds upper_bound for rule 1 in 'spades'. Reversing bounds."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_return_bool_for_missing_tool_fields(self, l):
        self.assertFalse(dt.parse_yaml(path=yt.ivYMLTest136, test=True, return_bool=True))
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Tool 'spades' does not have rules nor a default_destination!")
        )

    @log_capture()
    def test_return_rule_for_missing_tool_fields(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest136, test=True), yt.iv136dict)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Tool 'spades' does not have rules nor a default_destination!"),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_return_bool_for_blank_tool(self, l):
        self.assertFalse(dt.parse_yaml(path=yt.ivYMLTest137, test=True, return_bool=True))
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Config section for tool 'spades' is blank!")
        )

    @log_capture()
    def test_return_rule_for_blank_tool(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest137, test=True), yt.iv137dict)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Config section for tool 'spades' is blank!"),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_return_bool_for_malformed_users(self, l):
        self.assertFalse(dt.parse_yaml(path=yt.ivYMLTest138, test=True, return_bool=True))
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Entry '123' in users for rule 1 in tool 'spades' is in an invalid format!"),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Supplied email 'invaliduser.email@com' for rule 1 in tool 'spades' is in an invalid format!")
        )

    @log_capture()
    def test_return_rule_for_malformed_users(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest138, test=True), yt.iv138dict)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Entry '123' in users for rule 1 in tool 'spades' is in an invalid format! Ignoring entry."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Supplied email 'invaliduser.email@com' for rule 1 in tool 'spades' is in an invalid format! Ignoring email."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_return_bool_for_no_users(self, l):
        self.assertFalse(dt.parse_yaml(path=yt.ivYMLTest139, test=True, return_bool=True))
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Couldn't find a list under 'users:'!")
        )

    @log_capture()
    def test_return_rule_for_no_users(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest139, test=True), yt.iv139dict)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Couldn't find a list under 'users:'! Ignoring rule."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_return_bool_for_malformed_user_email(self, l):
        self.assertFalse(dt.parse_yaml(path=yt.ivYMLTest140, test=True, return_bool=True))
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Supplied email 'invalid.user2@com' for rule 2 in tool 'spades' is in an invalid format!"),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Supplied email 'invalid.user1@com' for rule 2 in tool 'spades' is in an invalid format!"),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "No valid user emails were specified for rule 2 in tool 'spades'!")
        )

    @log_capture()
    def test_return_rule_for_malformed_user_email(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest140, test=True), yt.iv140dict)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Supplied email 'invalid.user2@com' for rule 2 in tool 'spades' is in an invalid format! Ignoring email."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Supplied email 'invalid.user1@com' for rule 2 in tool 'spades' is in an invalid format! Ignoring email."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "No valid user emails were specified for rule 2 in tool 'spades'! Ignoring rule."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_return_bool_for_empty_users(self, l):
        self.assertFalse(dt.parse_yaml(path=yt.ivYMLTest141, test=True, return_bool=True))
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Entry 'None' in users for rule 2 in tool 'spades' is in an invalid format!"),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Entry 'None' in users for rule 2 in tool 'spades' is in an invalid format!"),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "No valid user emails were specified for rule 2 in tool 'spades'!")
        )

    @log_capture()
    def test_return_rule_for_empty_users(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest141, test=True), yt.iv141dict)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Entry 'None' in users for rule 2 in tool 'spades' is in an invalid format! Ignoring entry."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Entry 'None' in users for rule 2 in tool 'spades' is in an invalid format! Ignoring entry."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "No valid user emails were specified for rule 2 in tool 'spades'! Ignoring rule."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_return_bool_for_bad_num_input_datasets_bounds(self, l):
        self.assertFalse(dt.parse_yaml(path=yt.ivYMLTest142, test=True, return_bool=True))
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Error: lower_bound is set to Infinity, but must be lower than upper_bound!"),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "lower_bound exceeds upper_bound for rule 1 in 'smalt'.")
        )

    @log_capture()
    def test_return_rule_for_bad_num_input_datasets_bound(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest142, test=True), yt.iv142dict)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Error: lower_bound is set to Infinity, but must be lower than upper_bound! Setting lower_bound to 0!"),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_return_bool_for_worse_num_input_datasets_bounds(self, l):
        self.assertFalse(dt.parse_yaml(path=yt.ivYMLTest143, test=True, return_bool=True))
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Error: lower_bound is set to Infinity, but must be lower than upper_bound!")
        )

    @log_capture()
    def test_return_rule_for_worse_num_input_datasets_bound(self, l):
        self.assertEquals(dt.parse_yaml(path=yt.ivYMLTest143, test=True), yt.iv143dict)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Error: lower_bound is set to Infinity, but must be lower than upper_bound! Setting lower_bound to 0!"),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_priority_default_destination_without_med_priority_destination(self, l):
        dt.parse_yaml(path=yt.ivYMLTest144, test=True)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "No default 'med' priority destination!"),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_priority_default_destination_with_invalid_priority_destination(self, l):
        dt.parse_yaml(path=yt.ivYMLTest145, test=True)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Invalid default priority destination 'mine' found in config!"),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_tool_without_med_priority_destination(self, l):
        dt.parse_yaml(path=yt.ivYMLTest146, test=True)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "No 'med' priority destination for rule 1 in 'smalt'. Ignoring..."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_tool_with_invalid_priority_destination(self, l):
        dt.parse_yaml(path=yt.ivYMLTest147, test=True)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "Invalid priority destination 'mine' for rule 1 in 'smalt'. Ignoring..."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

    @log_capture()
    def test_users_with_invalid_priority(self, l):
        dt.parse_yaml(path=yt.ivYMLTest148, test=True)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', "User 'user@email.com', priority is not valid! Must be either low, med, or high."),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.')
        )

# ================================Valid yaml files==============================
    @log_capture()
    def test_parse_valid_yml(self, l):
        self.assertEqual(dt.parse_yaml(yt.vYMLTest1, test=True), yt.vdictTest1_yml)
        self.assertEqual(dt.parse_yaml(yt.vYMLTest2, test=True), yt.vdictTest2_yml)
        self.assertEqual(dt.parse_yaml(yt.vYMLTest3, test=True), yt.vdictTest3_yml)
        self.assertTrue(dt.parse_yaml(yt.vYMLTest4, test=True, return_bool=True))
        self.assertEqual(dt.parse_yaml(yt.vYMLTest4, test=True), yt.vdictTest4_yml)
        self.assertTrue(dt.parse_yaml(yt.vYMLTest5, test=True, return_bool=True))
        self.assertEqual(dt.parse_yaml(yt.vYMLTest5, test=True), yt.vdictTest5_yml)
        self.assertTrue(dt.parse_yaml(yt.vYMLTest6, test=True, return_bool=True))
        self.assertEqual(dt.parse_yaml(yt.vYMLTest6, test=True), yt.vdictTest6_yml)
        self.assertTrue(dt.parse_yaml(yt.vYMLTest7, test=True, return_bool=True))
        self.assertEqual(dt.parse_yaml(yt.vYMLTest7, test=True), yt.vdictTest7_yml)
        l.check(
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Running config validation...'),
            ('galaxy.jobs.dynamic_tool_destination', 'DEBUG', 'Finished config validation.'),
        )

# ================================Testing str_to_bytes==========================
    def test_str_to_bytes_invalid(self):
        self.assertRaises(dt.MalformedYMLException, dt.str_to_bytes, "1d")
        self.assertRaises(dt.MalformedYMLException, dt.str_to_bytes, "1 d")

    def test_str_to_bytes_valid(self):
        self.assertEqual(dt.str_to_bytes("-1"), -1)
        self.assertEqual(dt.str_to_bytes( "1" ), value)
        self.assertEqual(dt.str_to_bytes( 156 ), 156)
        self.assertEqual(dt.str_to_bytes( "1 B" ), value)
        self.assertEqual(dt.str_to_bytes( "1 KB" ), valueK)
        self.assertEqual(dt.str_to_bytes( "1 MB" ), valueM)
        self.assertEqual(dt.str_to_bytes( "1 gB" ), valueG)
        self.assertEqual(dt.str_to_bytes( "1 Tb" ), valueT)
        self.assertEqual(dt.str_to_bytes( "1 pb" ), valueP)
        self.assertEqual(dt.str_to_bytes( "1 EB" ), valueE)
        self.assertEqual(dt.str_to_bytes( "1 ZB" ), valueZ)
        self.assertEqual(dt.str_to_bytes( "1 YB" ), valueY)

# ==============================Testing bytes_to_str=============================
    @log_capture()
    def test_bytes_to_str_invalid(self, l):
        testValue = ""
        self.assertRaises( ValueError, dt.bytes_to_str, testValue )
        testValue = "5564fads"
        self.assertRaises( ValueError, dt.bytes_to_str, testValue )
        testValue = "45.0.1"
        self.assertRaises( ValueError, dt.bytes_to_str, testValue )
        self.assertRaises( ValueError, dt.bytes_to_str, "1 024" )

    def test_bytes_to_str_valid(self):
        self.assertEqual(dt.bytes_to_str(-1), "Infinity")
        self.assertEqual(dt.bytes_to_str( value), "1.00 B")
        self.assertEqual(dt.bytes_to_str( valueK), "1.00 KB")
        self.assertEqual(dt.bytes_to_str( valueM), "1.00 MB")
        self.assertEqual(dt.bytes_to_str( valueG), "1.00 GB")
        self.assertEqual(dt.bytes_to_str( valueT ), "1.00 TB")
        self.assertEqual(dt.bytes_to_str( valueP ), "1.00 PB")
        self.assertEqual(dt.bytes_to_str( valueE ), "1.00 EB")
        self.assertEqual(dt.bytes_to_str( valueZ ), "1.00 ZB")
        self.assertEqual(dt.bytes_to_str( valueY ), "1.00 YB")

        self.assertEqual(dt.bytes_to_str( 10, "B" ), "10.00 B")
        self.assertEqual(dt.bytes_to_str( 1000000, "KB" ), "976.56 KB")
        self.assertEqual(dt.bytes_to_str( 1000000000, "MB" ), "953.67 MB")
        self.assertEqual(dt.bytes_to_str( 1000000000000, "GB" ), "931.32 GB")
        self.assertEqual(dt.bytes_to_str( 1000000000000000, "TB" ), "909.49 TB")
        self.assertEqual(dt.bytes_to_str( 1000000000000000000, "PB" ), "888.18 PB")
        self.assertEqual(dt.bytes_to_str( 1000000000000000000000, "EB" ), "867.36 EB")
        self.assertEqual(dt.bytes_to_str( 1000000000000000000000000, "ZB" ), "847.03 ZB")

        self.assertEqual(dt.bytes_to_str( value, "KB" ), "1.00 B")
        self.assertEqual(dt.bytes_to_str( valueK, "MB" ), "1.00 KB")
        self.assertEqual(dt.bytes_to_str( valueM, "GB" ), "1.00 MB")
        self.assertEqual(dt.bytes_to_str( valueG, "TB" ), "1.00 GB")
        self.assertEqual(dt.bytes_to_str( valueT, "PB" ), "1.00 TB")
        self.assertEqual(dt.bytes_to_str( valueP, "EB" ), "1.00 PB")
        self.assertEqual(dt.bytes_to_str( valueE, "ZB" ), "1.00 EB")
        self.assertEqual(dt.bytes_to_str( valueZ, "YB" ), "1.00 ZB")

        self.assertEqual(dt.bytes_to_str( "1" ), "1.00 B")
        self.assertEqual(dt.bytes_to_str( "\t\t1000000" ), "976.56 KB")
        self.assertEqual(dt.bytes_to_str( "1000000000\n" ), "953.67 MB")
        self.assertEqual(dt.bytes_to_str( 1024, "fda" ), "1.00 KB")


if __name__ == '__main__':
    unittest.main()
