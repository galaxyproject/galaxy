/* global QUnit */
import _ from "underscore";
import testApp from "../test-app";
import testData from "../test-data/job-dag-1";
import JobDAG from "mvc/history/job-dag";

QUnit.module("mvc/history/job-dag.js tests", {
    beforeEach: function () {
        testApp.create();
    },
    afterEach: function () {
        testApp.destroy();
    },
});

// ------------------------------------------------------------------------
QUnit.test("Empty JobDAG construction", function (assert) {
    var dag = new JobDAG();
    assert.ok(dag instanceof JobDAG);

    // default options
    assert.deepEqual(dag.filters, []);
    assert.deepEqual(dag.options, {
        excludeSetMetadata: false,
    });

    // test (empty) instance vars
    assert.deepEqual(dag._jobsData, []);
    assert.deepEqual(dag._historyContentsMap, {});
    assert.deepEqual(dag._toolMap, {});
    assert.equal(dag.noInputJobs.length, 0);
    assert.equal(dag.noOutputJobs.length, 0);

    // logging
    assert.equal(typeof dag.debug, "function");
    assert.equal(typeof dag.info, "function");
    assert.equal(typeof dag.warn, "function");
    assert.equal(typeof dag.error, "function");
});

QUnit.test("Empty JobDAG construction - changing options", function (assert) {
    var dag;
    dag = new JobDAG({
        excludeSetMetadata: true,
    });

    // excludeSetMetadata
    assert.deepEqual(dag.options, {
        excludeSetMetadata: true,
    });
    assert.equal(dag.filters.length, 1);
    assert.equal(typeof dag.filters[0], "function");

    // filters
    function testFilter(job, index, jobData) {
        return true;
    }
    dag = new JobDAG({
        filters: [testFilter],
    });
    assert.equal(dag.filters[0], testFilter);
});

QUnit.test("JobDAG construction with history and jobs", function (assert) {
    assert.equal(testData.jobs1.length, 3);
    assert.equal(testData.historyContents1.length, 3);

    var history = testData.historyContents1,
        jobs = testData.jobs1,
        dag;
    dag = new JobDAG({
        historyContents: history,
        tools: testData.tools,
        jobs: jobs,
    });

    assert.deepEqual(dag._outputIdToJobMap, {
        "8c959c9304a2bc4b": "8a81cf6f989c4467",
        "132016f833b57406": "6505e875ddb66fd2",
        "846fb0a2a64137c0": "77f74776fd03cbc5",
    });
    assert.deepEqual(dag._jobsData, [
        {
            job: _.findWhere(jobs, { id: "8a81cf6f989c4467" }),
            inputs: {},
            outputs: {
                "8c959c9304a2bc4b": {
                    src: "hda",
                    id: "8c959c9304a2bc4b",
                    name: "output0",
                    content: _.findWhere(history, { id: "8c959c9304a2bc4b" }),
                },
            },
            tool: {},
        },
        {
            job: _.findWhere(jobs, { id: "6505e875ddb66fd2" }),
            inputs: {
                "8c959c9304a2bc4b": {
                    src: "hda",
                    id: "8c959c9304a2bc4b",
                    name: "input",
                    content: _.findWhere(history, { id: "8c959c9304a2bc4b" }),
                },
            },
            outputs: {
                "132016f833b57406": {
                    src: "hda",
                    id: "132016f833b57406",
                    name: "out_file1",
                    content: _.findWhere(history, { id: "132016f833b57406" }),
                },
            },
            tool: {},
        },
        {
            job: _.findWhere(jobs, { id: "77f74776fd03cbc5" }),
            inputs: {
                "132016f833b57406": {
                    src: "hda",
                    id: "132016f833b57406",
                    name: "input",
                    content: _.findWhere(history, { id: "132016f833b57406" }),
                },
            },
            outputs: {
                "846fb0a2a64137c0": {
                    src: "hda",
                    id: "846fb0a2a64137c0",
                    name: "out_file1",
                    content: _.findWhere(history, { id: "846fb0a2a64137c0" }),
                },
            },
            tool: {},
        },
    ]);

    var jobsDataMap = dag._jobsDataMap();
    assert.deepEqual(dag.toNodesAndLinks(), {
        nodes: [
            { name: "8a81cf6f989c4467", data: jobsDataMap["8a81cf6f989c4467"] },
            { name: "6505e875ddb66fd2", data: jobsDataMap["6505e875ddb66fd2"] },
            { name: "77f74776fd03cbc5", data: jobsDataMap["77f74776fd03cbc5"] },
        ],
        links: [
            { source: 0, target: 1, data: { dataset: "8c959c9304a2bc4b" } },
            { source: 1, target: 2, data: { dataset: "132016f833b57406" } },
        ],
    });

    assert.deepEqual(dag.toVerticesAndEdges(), {
        vertices: [
            { name: "8a81cf6f989c4467", data: jobsDataMap["8a81cf6f989c4467"] },
            { name: "6505e875ddb66fd2", data: jobsDataMap["6505e875ddb66fd2"] },
            { name: "77f74776fd03cbc5", data: jobsDataMap["77f74776fd03cbc5"] },
        ],
        edges: [
            {
                source: "8a81cf6f989c4467",
                target: "6505e875ddb66fd2",
                data: { dataset: "8c959c9304a2bc4b" },
            },
            {
                source: "6505e875ddb66fd2",
                target: "77f74776fd03cbc5",
                data: { dataset: "132016f833b57406" },
            },
        ],
    });

    // test cloning
});

QUnit.test("JobDAG removal of __SET_METADATA__ jobs", function (assert) {
    assert.equal(testData.jobs2.length, 3);
    assert.equal(testData.historyContents2.length, 2);

    var history = testData.historyContents2,
        jobs = testData.jobs2,
        dag;
    dag = new JobDAG({
        historyContents: history,
        tools: testData.tools,
        jobs: jobs,
        excludeSetMetadata: true,
    });

    var jobsDataMap = dag._jobsDataMap();
    assert.deepEqual(dag.toNodesAndLinks(), {
        nodes: [
            { name: "bf60fd5f5f7f44bf", data: jobsDataMap["bf60fd5f5f7f44bf"] },
            { name: "90240358ebde1489", data: jobsDataMap["90240358ebde1489"] },
        ],
        links: [{ source: 0, target: 1, data: { dataset: "eca0af6fb47bf90c" } }],
    });
});

//TODO: test filtering out errored jobs
QUnit.test("JobDAG construction with history and jobs", function (assert) {
    assert.equal(testData.jobs3.length, 5);
    assert.equal(testData.historyContents3.length, 5);

    var history = testData.historyContents3,
        jobs = testData.jobs3,
        dag;
    dag = new JobDAG({
        historyContents: history,
        tools: testData.tools,
        jobs: jobs,
    });

    var jobsDataMap = dag._jobsDataMap();
    assert.deepEqual(dag.toVerticesAndEdges(), {
        vertices: [
            { name: "8c959c9304a2bc4b", data: jobsDataMap["8c959c9304a2bc4b"] },
            { name: "132016f833b57406", data: jobsDataMap["132016f833b57406"] },
            { name: "846fb0a2a64137c0", data: jobsDataMap["846fb0a2a64137c0"] },
            { name: "eca0af6fb47bf90c", data: jobsDataMap["eca0af6fb47bf90c"] },
            { name: "6fc9fbb81c497f69", data: jobsDataMap["6fc9fbb81c497f69"] },
        ],
        edges: [
            {
                source: "8c959c9304a2bc4b",
                target: "846fb0a2a64137c0",
                data: { dataset: "6fb17d0cc6e8fae5" },
            },
            {
                source: "132016f833b57406",
                target: "eca0af6fb47bf90c",
                data: { dataset: "5114a2a207b7caff" },
            },
            {
                source: "eca0af6fb47bf90c",
                target: "6fc9fbb81c497f69",
                data: { dataset: "b8a0d6158b9961df" },
            },
        ],
    });

    var components = dag.weakComponents();
    assert.deepEqual(components, [
        {
            vertices: [
                { name: "8c959c9304a2bc4b", data: jobsDataMap["8c959c9304a2bc4b"] },
                { name: "846fb0a2a64137c0", data: jobsDataMap["846fb0a2a64137c0"] },
            ],
            edges: [{ source: "8c959c9304a2bc4b", target: "846fb0a2a64137c0" }],
        },
        {
            vertices: [
                { name: "132016f833b57406", data: jobsDataMap["132016f833b57406"] },
                { name: "eca0af6fb47bf90c", data: jobsDataMap["eca0af6fb47bf90c"] },
                { name: "6fc9fbb81c497f69", data: jobsDataMap["6fc9fbb81c497f69"] },
            ],
            edges: [
                { source: "132016f833b57406", target: "eca0af6fb47bf90c" },
                { source: "eca0af6fb47bf90c", target: "6fc9fbb81c497f69" },
            ],
        },
    ]);
});

//TODO: test filtering out errored jobs
QUnit.test("JobDAG construction with copied history contents", function (assert) {
    assert.equal(testData.jobs4.length, 1);
    assert.equal(testData.historyContents4.length, 3);

    var history = testData.historyContents4,
        jobs = testData.jobs4,
        dag;
    dag = new JobDAG({
        historyContents: history,
        tools: testData.tools,
        jobs: jobs,
    });

    var jobsDataMap = dag._jobsDataMap();
    assert.deepEqual(dag.toVerticesAndEdges(), {
        vertices: [
            { name: "92b83968e0b52980", data: jobsDataMap["92b83968e0b52980"] },
            { name: "copy-422eef6b1b545329", data: _.findWhere(history, { id: "422eef6b1b545329" }) },
            { name: "copy-c86c1b73aa7102dd", data: _.findWhere(history, { id: "c86c1b73aa7102dd" }) },
        ],
        edges: [
            {
                source: "copy-422eef6b1b545329",
                target: "92b83968e0b52980",
                data: { dataset: "422eef6b1b545329" },
            },
            {
                source: "copy-c86c1b73aa7102dd",
                target: "92b83968e0b52980",
                data: { dataset: "c86c1b73aa7102dd" },
            },
        ],
    });
});
