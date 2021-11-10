// Load all qunit tests into a single bundle.
//var testsContext = require.context(".", true, /_tests$/);
//testsContext.keys().forEach(testsContext);

import "./tests/galaxy_app_base_tests";
import "./tests/jquery_plugin_tests";
import "./tests/metrics_logger_tests";
import "./tests/workflow_editor_tests";
import "./tests/graph_tests";
import "./tests/job_dag_tests";
import "./tests/history_contents_model_tests";
import "./tests/hda_base_tests";
import "./tests/modal_tests";
import "./tests/utils_tests";
import "./tests/ui_tests";
