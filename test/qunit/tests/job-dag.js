define([
    "mvc/history/job-dag",
    "jquery",
    "sinon-qunit",
    'test-data/job-dag-1'
], function( JobDAG, $, sinon, testData ){
    console.debug( '' );
    
    /*globals equal ok, test module expect deepEqual strictEqual */
    "use strict";

    module( "mvc/history/job-dag.js tests" );
///*
    function testEmptyObject( o ){
        ok( typeof o === 'object' );
        ok( Object.keys( o ).length === 0 );
    }

    // ------------------------------------------------------------------------
    test( "Empty JobDAG construction", function() {
        var dag = new JobDAG();
        ok( dag instanceof JobDAG );

        // test (empty) instance vars
        testEmptyObject( dag._historyContentsMap );
        equal( dag.filters.length, 0 );

        testEmptyObject( dag._idMap );
        equal( dag.noInputJobs.length, 0 );
        equal( dag.noOutputJobs.length, 0 );

        // default options
        deepEqual( dag.options, {
            excludeSetMetadata : false
        });

        // logging
        equal( typeof dag.debug, 'function' );
        equal( typeof dag.info, 'function' );
        equal( typeof dag.warn, 'function' );
        equal( typeof dag.error, 'function' );
    });

    test( "Empty JobDAG construction - changing options", function() {
        var dag;
        dag = new JobDAG({
            excludeSetMetadata : true
        });

        // excludeSetMetadata
        deepEqual( dag.options, {
            excludeSetMetadata : true
        });
        equal( dag.filters.length, 1 );
        equal( typeof dag.filters[0], 'function' );

        // filters
        function testFilter( job, index, jobData ){ return true; }
        dag = new JobDAG({
            filters : [ testFilter ]
        });
        equal( dag.filters[0], testFilter );
    });

    test( "JobDAG construction with history and jobs", function() {
        equal( testData.jobs1.length, 3 );
        equal( testData.historyContents1.length, 3 );

        var history = testData.historyContents1,
            jobs = testData.jobs1,
            dag;
        dag = new JobDAG({
            historyContents : history,
            jobs : jobs
        });
        deepEqual( Object.keys( dag._historyContentsMap ),
                   [ "8c959c9304a2bc4b", "132016f833b57406", "846fb0a2a64137c0" ] );
        deepEqual( dag._idMap, {
            "8a81cf6f989c4467": {
                "index": 0,
                "job": _.findWhere( jobs, { id : "8a81cf6f989c4467" }),
                "inputs": [],
                "outputs": [ "8c959c9304a2bc4b" ],
                "usedIn": [ { "job": "6505e875ddb66fd2", "output": "8c959c9304a2bc4b" } ]
            },
            "6505e875ddb66fd2": {
                "index": 1,
                "job": _.findWhere( jobs, { id : "6505e875ddb66fd2" }),
                "inputs": [ "8c959c9304a2bc4b" ],
                "outputs": [ "132016f833b57406" ],
                "usedIn": [ { "job": "77f74776fd03cbc5", "output": "132016f833b57406" } ]
            },
            "77f74776fd03cbc5": {
                "index": 2,
                "job": _.findWhere( jobs, { id : "77f74776fd03cbc5" }),
                "inputs": [ "132016f833b57406" ],
                "outputs": [ "846fb0a2a64137c0" ],
                "usedIn": []
            }
        });

        deepEqual( dag.toNodesAndLinks(), {
            "nodes": [
                { "name": "8a81cf6f989c4467", "data": dag._idMap[ "8a81cf6f989c4467" ] },
                { "name": "6505e875ddb66fd2", "data": dag._idMap[ "6505e875ddb66fd2" ] },
                { "name": "77f74776fd03cbc5", "data": dag._idMap[ "77f74776fd03cbc5" ] }
            ],
            "links": [
                { "source": 0, "target": 1, "data": { "dataset": "8c959c9304a2bc4b" } },
                { "source": 1, "target": 2, "data": { "dataset": "132016f833b57406" } }
            ]
        });

        deepEqual( dag.toVerticesAndEdges(), {
            "vertices": [
                { "name": "8a81cf6f989c4467", "data": dag._idMap[ "8a81cf6f989c4467" ] },
                { "name": "6505e875ddb66fd2", "data": dag._idMap[ "6505e875ddb66fd2" ] },
                { "name": "77f74776fd03cbc5", "data": dag._idMap[ "77f74776fd03cbc5" ] }
            ],
            "edges": [
                { "source": "8a81cf6f989c4467", "target": "6505e875ddb66fd2",
                  "data": { "dataset": "8c959c9304a2bc4b" } },
                { "source": "6505e875ddb66fd2", "target": "77f74776fd03cbc5",
                  "data": { "dataset": "132016f833b57406" } }
            ]
        });

        // test cloning
    });

    test( "JobDAG removal of __SET_METADATA__ jobs", function() {
        equal( testData.jobs2.length, 3 );
        equal( testData.historyContents2.length, 2 );

        var history = testData.historyContents2,
            jobs = testData.jobs2,
            dag;
        dag = new JobDAG({
            historyContents : history,
            jobs : jobs,
            excludeSetMetadata : true
        });
        deepEqual( Object.keys( dag._idMap ),
                   [ "bf60fd5f5f7f44bf", "90240358ebde1489" ] );

        deepEqual( dag._idMap, {
            "bf60fd5f5f7f44bf": {
                "index": 0,
                "job": _.findWhere( jobs, { id : "bf60fd5f5f7f44bf" }),
                "inputs": [],
                "outputs": [ "eca0af6fb47bf90c" ],
                "usedIn": [ { "job": "90240358ebde1489", "output": "eca0af6fb47bf90c" } ]
            },
            "90240358ebde1489": {
                "index": 1,
                "job": _.findWhere( jobs, { id : "90240358ebde1489" }),
                "inputs": [ "eca0af6fb47bf90c" ],
                "outputs": [ "6fc9fbb81c497f69" ],
                "usedIn": []
            }
        });
        deepEqual( dag.toNodesAndLinks(), {
            "nodes": [
                { "name": "bf60fd5f5f7f44bf", "data": dag._idMap[ "bf60fd5f5f7f44bf" ] },
                { "name": "90240358ebde1489", "data": dag._idMap[ "90240358ebde1489" ] }
            ],
            "links": [
                { "source": 0, "target": 1, "data": { "dataset": "eca0af6fb47bf90c" } }
            ]
        });
    });

    //TODO: test filtering out errored jobs
    test( "JobDAG construction with history and jobs", function() {
        equal( testData.jobs3.length, 5 );
        equal( testData.historyContents3.length, 5 );

        var history = testData.historyContents3,
            jobs = testData.jobs3,
            dag;
        dag = new JobDAG({
            historyContents : history,
            jobs : jobs
        });
        deepEqual( Object.keys( dag._historyContentsMap ), [
            "6fb17d0cc6e8fae5", "5114a2a207b7caff", "06ec17aefa2d49dd", "b8a0d6158b9961df", "24d84bcf64116fe7" ] );

        deepEqual( dag.toVerticesAndEdges(), {
            "vertices": [
                { "name": "8c959c9304a2bc4b", "data": dag._idMap[ "8c959c9304a2bc4b" ] },
                { "name": "846fb0a2a64137c0", "data": dag._idMap[ "846fb0a2a64137c0" ] },
                { "name": "132016f833b57406", "data": dag._idMap[ "132016f833b57406" ] },
                { "name": "eca0af6fb47bf90c", "data": dag._idMap[ "eca0af6fb47bf90c" ] },
                { "name": "6fc9fbb81c497f69", "data": dag._idMap[ "6fc9fbb81c497f69" ] }
            ],
            "edges": [
                { "source": "8c959c9304a2bc4b", "target": "846fb0a2a64137c0",
                    "data": { "dataset": "6fb17d0cc6e8fae5" } },
                { "source": "132016f833b57406", "target": "eca0af6fb47bf90c",
                    "data": { "dataset": "5114a2a207b7caff" } },
                { "source": "eca0af6fb47bf90c", "target": "6fc9fbb81c497f69",
                    "data": { "dataset": "b8a0d6158b9961df" } }
            ]
        });

        var components = dag.weakComponents();
        deepEqual( components, [
            {
                "vertices": [
                    { "name": "8c959c9304a2bc4b", "data": dag._idMap[ "8c959c9304a2bc4b" ] },
                    { "name": "846fb0a2a64137c0", "data": dag._idMap[ "846fb0a2a64137c0" ] }
                ],
                "edges": [
                    { "source": "8c959c9304a2bc4b", "target": "846fb0a2a64137c0" }
                ]
            },
            {
                "vertices": [
                    { "name": "132016f833b57406", "data": dag._idMap[ "132016f833b57406" ] },
                    { "name": "eca0af6fb47bf90c", "data": dag._idMap[ "eca0af6fb47bf90c" ] },
                    { "name": "6fc9fbb81c497f69", "data": dag._idMap[ "6fc9fbb81c497f69" ] }
                ],
                "edges": [
                    { "source": "132016f833b57406", "target": "eca0af6fb47bf90c" },
                    { "source": "eca0af6fb47bf90c", "target": "6fc9fbb81c497f69" }
                ]
            }
        ]);

    });

});
