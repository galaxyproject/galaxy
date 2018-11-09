// Load all qunit tests into a single bundle.
//var testsContext = require.context(".", true, /_tests$/);
//testsContext.keys().forEach(testsContext);

import "qunit/tests/galaxy_app_base_tests";
import "qunit/tests/jquery_plugin_tests";
import "qunit/tests/metrics_logger_tests";

// form_tests seems to need to come before something - maybe multiple things
import "qunit/tests/form_tests";

import "qunit/tests/list_of_pairs_collection_creator_tests";
import "qunit/tests/upload_dialog_tests";
import "qunit/tests/workflow_editor_tests";
import "qunit/tests/masthead_tests";
import "qunit/tests/graph_tests";
import "qunit/tests/job_dag_tests";
import "qunit/tests/history_contents_model_tests";
import "qunit/tests/hda_base_tests";
import "qunit/tests/modal_tests";
import "qunit/tests/page_tests";
import "qunit/tests/utils_tests";
import "qunit/tests/ui_tests";

