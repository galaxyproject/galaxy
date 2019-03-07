// ============================================================================
var tools = {
    upload1: {},
    "Show beginning1": {},
    "Show tail1": {},
    random_lines1: {},
    __SET_METADATA__: {},
    cat1: {}
};

// ============================================================================
// plain 3 step job chain
var jobs1 = [
    {
        tool_id: "upload1",
        update_time: "2014-10-03T15:12:25.904033",
        inputs: {},
        outputs: {
            output0: {
                src: "hda",
                id: "8c959c9304a2bc4b"
            }
        },
        exit_code: 0,
        state: "ok",
        create_time: "2014-10-03T15:12:22.589152",
        params: {
            // ...
        },
        model_class: "Job",
        id: "8a81cf6f989c4467",
        tool: null
    },
    {
        tool_id: "Show beginning1",
        update_time: "2014-10-03T15:14:04.328484",
        inputs: {
            input: {
                src: "hda",
                id: "8c959c9304a2bc4b"
            }
        },
        outputs: {
            out_file1: {
                src: "hda",
                id: "132016f833b57406"
            }
        },
        exit_code: 0,
        state: "ok",
        create_time: "2014-10-03T15:14:01.060662",
        params: {
            // ...
        },
        model_class: "Job",
        id: "6505e875ddb66fd2",
        tool: null
    },
    {
        tool_id: "Show tail1",
        update_time: "2014-10-03T15:14:21.596871",
        inputs: {
            input: {
                src: "hda",
                id: "132016f833b57406"
            }
        },
        outputs: {
            out_file1: {
                src: "hda",
                id: "846fb0a2a64137c0"
            }
        },
        exit_code: 0,
        state: "ok",
        create_time: "2014-10-03T15:14:18.425681",
        params: {
            // ...
        },
        model_class: "Job",
        id: "77f74776fd03cbc5",
        tool: null
    }
];

var historyContents1 = [
    {
        deleted: false,
        extension: "interval",
        hid: 1,
        history_content_type: "dataset",
        history_id: "911dde3ddb677bcd",
        id: "8c959c9304a2bc4b",
        name: "1.interval",
        purged: false,
        resubmitted: false,
        state: "ok",
        type: "file",
        url: "/api/histories/911dde3ddb677bcd/contents/datasets/8c959c9304a2bc4b",
        visible: true
    },
    {
        deleted: false,
        extension: "interval",
        hid: 2,
        history_content_type: "dataset",
        history_id: "911dde3ddb677bcd",
        id: "132016f833b57406",
        name: "Select first on data 1",
        purged: false,
        resubmitted: false,
        state: "ok",
        type: "file",
        url: "/api/histories/911dde3ddb677bcd/contents/datasets/132016f833b57406",
        visible: true
    },
    {
        deleted: false,
        extension: "interval",
        hid: 3,
        history_content_type: "dataset",
        history_id: "911dde3ddb677bcd",
        id: "846fb0a2a64137c0",
        name: "Select last on data 2",
        purged: false,
        resubmitted: false,
        state: "ok",
        type: "file",
        url: "/api/histories/911dde3ddb677bcd/contents/datasets/846fb0a2a64137c0",
        visible: true
    }
];

// ============================================================================
// single job chain with a __SET_METADATA__ job
var jobs2 = [
    {
        tool_id: "upload1",
        update_time: "2014-10-03T16:09:49.590769",
        inputs: {},
        outputs: {
            output0: {
                src: "hda",
                id: "eca0af6fb47bf90c"
            }
        },
        exit_code: 0,
        state: "ok",
        create_time: "2014-10-03T16:09:45.190023",
        params: {
            // ...
        },
        model_class: "Job",
        id: "bf60fd5f5f7f44bf",
        tool: null
    },
    {
        tool_id: "random_lines1",
        update_time: "2014-10-03T16:10:44.743610",
        inputs: {
            input: {
                src: "hda",
                id: "eca0af6fb47bf90c"
            }
        },
        outputs: {
            out_file1: {
                src: "hda",
                id: "6fc9fbb81c497f69"
            }
        },
        exit_code: 0,
        state: "ok",
        create_time: "2014-10-03T16:10:41.446413",
        params: {
            // ...
        },
        model_class: "Job",
        id: "90240358ebde1489",
        tool: null
    },
    {
        tool_id: "__SET_METADATA__",
        update_time: "2014-10-03T16:14:44.196697",
        inputs: {
            input1: {
                src: "hda",
                id: "eca0af6fb47bf90c"
            }
        },
        outputs: {},
        exit_code: 0,
        state: "ok",
        create_time: "2014-10-03T16:14:37.901222",
        params: {
            // ...
        },
        model_class: "Job",
        id: "86cf1d3beeec9f1c",
        tool: null
    }
];

var historyContents2 = [
    {
        deleted: false,
        extension: "interval",
        hid: 1,
        history_content_type: "dataset",
        history_id: "ff5476bcf6c921fa",
        id: "eca0af6fb47bf90c",
        name: "1.interval",
        purged: false,
        resubmitted: false,
        state: "ok",
        type: "file",
        url: "/api/histories/ff5476bcf6c921fa/contents/datasets/eca0af6fb47bf90c",
        visible: true
    },
    {
        deleted: false,
        extension: "interval",
        hid: 2,
        history_content_type: "dataset",
        history_id: "ff5476bcf6c921fa",
        id: "6fc9fbb81c497f69",
        name: "Select random lines on data 1",
        purged: false,
        resubmitted: false,
        state: "ok",
        type: "file",
        url: "/api/histories/ff5476bcf6c921fa/contents/datasets/6fc9fbb81c497f69",
        visible: true
    }
];

var jobs3 = [
    {
        tool_id: "upload1",
        update_time: "2014-10-13T20:28:58.549844",
        inputs: {},
        outputs: {
            output0: {
                src: "hda",
                id: "6fb17d0cc6e8fae5"
            }
        },
        exit_code: 0,
        state: "ok",
        create_time: "2014-10-13T20:28:43.162803",
        params: {
            // ...
        },
        model_class: "Job",
        id: "8c959c9304a2bc4b",
        tool: null
    },
    {
        tool_id: "upload1",
        update_time: "2014-10-13T20:28:58.932152",
        inputs: {},
        outputs: {
            output0: {
                src: "hda",
                id: "5114a2a207b7caff"
            }
        },
        exit_code: 0,
        state: "ok",
        create_time: "2014-10-13T20:28:47.421452",
        params: {
            // ...
        },
        model_class: "Job",
        id: "132016f833b57406",
        tool: null
    },
    {
        tool_id: "Show beginning1",
        update_time: "2014-10-13T20:29:31.424058",
        inputs: {
            input: {
                src: "hda",
                id: "6fb17d0cc6e8fae5"
            }
        },
        outputs: {
            out_file1: {
                src: "hda",
                id: "06ec17aefa2d49dd"
            }
        },
        exit_code: 0,
        state: "ok",
        create_time: "2014-10-13T20:29:28.769495",
        params: {
            // ...
        },
        model_class: "Job",
        id: "846fb0a2a64137c0",
        tool: null
    },
    {
        tool_id: "Show beginning1",
        update_time: "2014-10-13T20:29:55.851096",
        inputs: {
            input: {
                src: "hda",
                id: "5114a2a207b7caff"
            }
        },
        outputs: {
            out_file1: {
                src: "hda",
                id: "b8a0d6158b9961df"
            }
        },
        exit_code: 0,
        state: "ok",
        create_time: "2014-10-13T20:29:53.291703",
        params: {
            // ...
        },
        model_class: "Job",
        id: "eca0af6fb47bf90c",
        tool: null
    },
    {
        tool_id: "Show tail1",
        update_time: "2014-10-13T20:30:16.225937",
        inputs: {
            input: {
                src: "hda",
                id: "b8a0d6158b9961df"
            }
        },
        outputs: {
            out_file1: {
                src: "hda",
                id: "24d84bcf64116fe7"
            }
        },
        exit_code: 0,
        state: "ok",
        create_time: "2014-10-13T20:30:13.789842",
        params: {
            // ...
        },
        model_class: "Job",
        id: "6fc9fbb81c497f69",
        tool: null
    }
];

var historyContents3 = [
    {
        deleted: false,
        extension: "bed",
        hid: 1,
        history_content_type: "dataset",
        history_id: "5564089c81cf7fe8",
        id: "6fb17d0cc6e8fae5",
        name: "1.bed",
        purged: false,
        resubmitted: false,
        state: "ok",
        type: "file",
        url: "/api/histories/5564089c81cf7fe8/contents/datasets/6fb17d0cc6e8fae5",
        visible: true
    },
    {
        deleted: false,
        extension: "interval",
        hid: 2,
        history_content_type: "dataset",
        history_id: "5564089c81cf7fe8",
        id: "5114a2a207b7caff",
        name: "1.interval",
        purged: false,
        resubmitted: false,
        state: "ok",
        type: "file",
        url: "/api/histories/5564089c81cf7fe8/contents/datasets/5114a2a207b7caff",
        visible: true
    },
    {
        deleted: false,
        extension: "bed",
        hid: 3,
        history_content_type: "dataset",
        history_id: "5564089c81cf7fe8",
        id: "06ec17aefa2d49dd",
        name: "Select first on data 1",
        purged: false,
        resubmitted: false,
        state: "ok",
        type: "file",
        url: "/api/histories/5564089c81cf7fe8/contents/datasets/06ec17aefa2d49dd",
        visible: true
    },
    {
        deleted: false,
        extension: "interval",
        hid: 4,
        history_content_type: "dataset",
        history_id: "5564089c81cf7fe8",
        id: "b8a0d6158b9961df",
        name: "Select first on data 2",
        purged: false,
        resubmitted: false,
        state: "ok",
        type: "file",
        url: "/api/histories/5564089c81cf7fe8/contents/datasets/b8a0d6158b9961df",
        visible: true
    },
    {
        deleted: false,
        extension: "interval",
        hid: 5,
        history_content_type: "dataset",
        history_id: "5564089c81cf7fe8",
        id: "24d84bcf64116fe7",
        name: "Select last on data 4",
        purged: false,
        resubmitted: false,
        state: "ok",
        type: "file",
        url: "/api/histories/5564089c81cf7fe8/contents/datasets/24d84bcf64116fe7",
        visible: true
    }
];

var jobs4 = [
    {
        tool_id: "cat1",
        update_time: "2014-10-21T17:33:36.960857",
        inputs: {
            input1: {
                src: "hda",
                id: "422eef6b1b545329",
                name: "input1"
            },
            "queries_0|input2": {
                src: "hda",
                id: "c86c1b73aa7102dd",
                name: "queries_0|input2"
            }
        },
        outputs: {
            out_file1: {
                src: "hda",
                id: "52d6bdfafedbb5e5",
                name: "out_file1"
            }
        },
        exit_code: 0,
        state: "ok",
        create_time: "2014-10-21T17:33:34.302245",
        params: {
            // ...
        },
        model_class: "Job",
        id: "92b83968e0b52980"
    }
];

var historyContents4 = [
    {
        dataset_id: 29,
        deleted: false,
        extension: "vcf",
        hid: 1,
        history_content_type: "dataset",
        history_id: "c24141d7e4e77705",
        id: "422eef6b1b545329",
        name: "1.vcf",
        purged: false,
        resubmitted: false,
        state: "ok",
        type: "file",
        url: "/api/histories/c24141d7e4e77705/contents/datasets/422eef6b1b545329",
        visible: true
    },
    {
        dataset_id: 56,
        deleted: false,
        extension: "maf",
        hid: 2,
        history_content_type: "dataset",
        history_id: "c24141d7e4e77705",
        id: "c86c1b73aa7102dd",
        name: "3.maf",
        purged: false,
        resubmitted: false,
        state: "ok",
        type: "file",
        url: "/api/histories/c24141d7e4e77705/contents/datasets/c86c1b73aa7102dd",
        visible: true
    },
    {
        dataset_id: 131,
        deleted: false,
        extension: "maf",
        hid: 3,
        history_content_type: "dataset",
        history_id: "c24141d7e4e77705",
        id: "52d6bdfafedbb5e5",
        name: "Concatenate datasets on data 1 and data 2",
        purged: false,
        resubmitted: false,
        state: "ok",
        type: "file",
        url: "/api/histories/c24141d7e4e77705/contents/datasets/52d6bdfafedbb5e5",
        visible: true
    }
];

// ============================================================================
export default {
    tools: tools,
    jobs1: jobs1,
    historyContents1: historyContents1,
    jobs2: jobs2,
    historyContents2: historyContents2,
    jobs3: jobs3,
    historyContents3: historyContents3,
    jobs4: jobs4,
    historyContents4: historyContents4
};
