define([
    "utils/graph",
    "jquery",
    "sinon-qunit"
], function( GRAPH, $, sinon ){

    /*globals equal ok, test module expect deepEqual strictEqual */
    "use strict";

    module( "utils/graph.js library tests" );
///*
    function testEmptyObject( o ){
        ok( typeof o === 'object' );
        ok( Object.keys( o ).length === 0 );
    }

    // ------------------------------------------------------------------------ vertices
    test( "Empty vertex construction", function() {
        var vert = new GRAPH.Vertex();
        ok( vert instanceof GRAPH.Vertex );
        ok( vert.name === '(unnamed)' );
        ok( vert.data === null );
        testEmptyObject( vert.edges );
        ok( vert.degree === 0 );
        ok( ( vert + '' ) === 'Vertex((unnamed))' );
        deepEqual( vert.toJSON(), { name : '(unnamed)', data: null });
    });

    test( "Vertex construction", function() {
        var vert = new GRAPH.Vertex( 'blah', { blorp: 1, bleep: 2 });
        ok( vert instanceof GRAPH.Vertex );
        ok( vert.name === 'blah' );
        deepEqual( vert.data, { blorp: 1, bleep: 2 });
        testEmptyObject( vert.edges );
        ok( vert.degree === 0 );
        ok( ( vert + '' ) === 'Vertex(blah)' );
        deepEqual( vert.toJSON(), { name : 'blah', data: { blorp: 1, bleep: 2 } });
    });

    // ------------------------------------------------------------------------ edges
    test( "Empty edge construction", function() {
        var edge = new GRAPH.Edge();
        ok( edge instanceof GRAPH.Edge );
        ok( edge.source === null );
        ok( edge.target === null );
        ok( edge.data === null );
        ok( ( edge + '' ) === 'null->null' );
        deepEqual( edge.toJSON(), { source : null, target: null });
    });

    test( "Edge construction", function() {
        var edge = new GRAPH.Edge( 'A', 'B', { one: 1, two: 2 });
        ok( edge instanceof GRAPH.Edge );
        ok( edge.source === 'A' );
        ok( edge.target === 'B' );
        deepEqual( edge.data, { one: 1, two: 2 } );
        ok( ( edge + '' ) === 'A->B' );
        deepEqual( edge.toJSON(), { source : 'A', target: 'B', data : { one: 1, two: 2 } });
    });

    // ------------------------------------------------------------------------ graphs
    function testEmptyGraph( graph ){
        ok( graph instanceof GRAPH.Graph );
        testEmptyObject( graph.vertices );
        ok( graph.numEdges === 0 );
    }

    test( "Empty graph construction", function() {
        var graph = new GRAPH.Graph();

        ok( graph.directed === false );
        ok( graph.allowReflexiveEdges === false );

        testEmptyGraph( graph );
    });

    test( "Bad data graph construction", function() {
        var graph = new GRAPH.Graph( false, {} );
        testEmptyGraph( graph );

        graph = new GRAPH.Graph( false, null );
        testEmptyGraph( graph );
    });

    test( "Test directed and options", function() {
        var graph = new GRAPH.Graph( true, {}, { allowReflexiveEdges : true });

        ok( graph.directed );
        ok( graph.allowReflexiveEdges );

        testEmptyGraph( graph );
    });

    function testSampleDirectedGraph( graph ){
        ok( !graph.directed );

        ok( Object.keys( graph.vertices ).length === 3 );
        ok( graph.vertices.A instanceof GRAPH.Vertex );
        ok( graph.vertices.B instanceof GRAPH.Vertex );
        ok( graph.vertices.C instanceof GRAPH.Vertex );

        deepEqual( Object.keys( graph.vertices.A.edges ), [ 'B', 'C' ] );
        deepEqual( Object.keys( graph.vertices.B.edges ), [ 'A', 'C' ] );
        deepEqual( Object.keys( graph.vertices.C.edges ), [ 'A', 'B' ] );

        ok( graph.vertices.A.degree === 2 );
        ok( graph.vertices.B.degree === 2 );
        ok( graph.vertices.C.degree === 2 );

        deepEqual( graph.vertices.A.edges.B.toJSON(), { source: 'A', target: 'B' });
        deepEqual( graph.vertices.A.edges.C.toJSON(), { source: 'A', target: 'C' });
        deepEqual( graph.vertices.B.edges.A.toJSON(), { source: 'B', target: 'A' });
        deepEqual( graph.vertices.B.edges.C.toJSON(), { source: 'B', target: 'C' });
        deepEqual( graph.vertices.C.edges.A.toJSON(), { source: 'C', target: 'A' });
        deepEqual( graph.vertices.C.edges.B.toJSON(), { source: 'C', target: 'B' });

        ok( graph.numEdges === 6 );
    }

    function testSampleNonDirectedGraph( graph ){
        ok( graph.directed );

        ok( Object.keys( graph.vertices ).length === 3 );
        ok( graph.vertices.A instanceof GRAPH.Vertex );
        ok( graph.vertices.B instanceof GRAPH.Vertex );
        ok( graph.vertices.C instanceof GRAPH.Vertex );

        deepEqual( Object.keys( graph.vertices.A.edges ), [ 'B', 'C' ] );
        deepEqual( Object.keys( graph.vertices.B.edges ), [ 'C' ] );
        deepEqual( Object.keys( graph.vertices.C.edges ), [] );

        ok( graph.vertices.A.degree === 2 );
        ok( graph.vertices.B.degree === 1 );
        ok( graph.vertices.C.degree === 0 );

        deepEqual( graph.vertices.A.edges.B.toJSON(), { source: 'A', target: 'B' });
        deepEqual( graph.vertices.A.edges.C.toJSON(), { source: 'A', target: 'C' });
        deepEqual( graph.vertices.B.edges.C.toJSON(), { source: 'B', target: 'C' });

        ok( graph.numEdges === 3 );
    }

    var nodeLinkData = {
        nodes : [
            { name : 'A', data: 100 },
            { name : 'B', data: 200 },
            { name : 'C', data: 300 }
        ],
        links : [
            { source: 0, target: 1 },
            { source: 0, target: 2 },
            { source: 1, target: 2 }
        ]
    };

    test( "Test nodes and links data input on *non-directed* graph", function() {
        var graph = new GRAPH.Graph( false, nodeLinkData );
        testSampleDirectedGraph( graph );
    });

    test( "Test nodes and links data input on *directed* graph", function() {
        var graph = new GRAPH.Graph( true, nodeLinkData );
        testSampleNonDirectedGraph( graph );
    });

    var vertexEdgeData = {
        vertices : [
            { name : 'A', data: 100 },
            { name : 'B', data: 200 },
            { name : 'C', data: 300 }
        ],
        edges : [
            { source: 'A', target: 'B' },
            { source: 'A', target: 'C' },
            { source: 'B', target: 'C' }
        ]
    };

    test( "Test vertex and edge data input on *non-directed* graph", function() {
        var graph = new GRAPH.Graph( false, vertexEdgeData );
        testSampleDirectedGraph( graph );
    });

    test( "Test vertex and edge data input on *directed* graph", function() {
        var graph = new GRAPH.Graph( true, vertexEdgeData );
        testSampleNonDirectedGraph( graph );
    });

    test( "Test vertex eachEdge", function() {
        var graph = new GRAPH.Graph( false, nodeLinkData );
        ok( typeof graph.vertices.A.eachEdge === 'function' );
        deepEqual( graph.vertices.A.eachEdge( function( e ){ return e.target; }), [ 'B', 'C' ] );
        ok( graph.vertices.A.eachEdge({ target: 'B' }).length === 1 );
    });

    test( "Test graph eachVertex", function() {
        var graph = new GRAPH.Graph( true, nodeLinkData );
        ok( typeof graph.eachVertex === 'function' );
        deepEqual( graph.eachVertex( function( v ){ return { n: v.name, d: v.degree }; }), [
            { n: 'A', d: 2 },
            { n: 'B', d: 1 },
            { n: 'C', d: 0 }
        ]);
        ok( graph.eachVertex({ degree: 2 })[0] === graph.vertices.A );
    });

    test( "Test createVertex", function() {
        var graph = new GRAPH.Graph();
        var vert1 = graph.createVertex( 'A', { blah: 1 });
        ok( vert1 instanceof GRAPH.Vertex );
        ok( vert1 === graph.vertices.A );
        ok( graph.createVertex( 'A', { blah: 1 } ) === vert1 );
    });

    test( "Test createEdge", function() {
        var graph, A, B, edge;

        graph = new GRAPH.Graph();
        A = graph.createVertex( 'A' );
        B = graph.createVertex( 'B' );
        edge = graph.createEdge( 'A', 'B' );
        ok( edge instanceof GRAPH.Edge );
        ok( A.degree === 1 );
        ok( B.degree === 1 );
        ok( A.edges.B );
        ok( B.edges.A );
        ok( graph.numEdges === 2 );

        // bad target
        graph = new GRAPH.Graph();
        A = graph.createVertex( 'A' );
        B = graph.createVertex( 'B' );
        edge = graph.createEdge( 'A', 'C' );
        ok( edge === null );
        ok( A.degree === 0 );
        ok( B.degree === 0 );
        ok( !A.edges.B );
        ok( !B.edges.A );
        ok( graph.numEdges === 0 );

        // bad source
        graph = new GRAPH.Graph();
        A = graph.createVertex( 'A' );
        B = graph.createVertex( 'B' );
        edge = graph.createEdge( 'C', 'A' );
        ok( graph.numEdges === 0 );

        // reflexive
        graph = new GRAPH.Graph();
        A = graph.createVertex( 'A' );
        B = graph.createVertex( 'B' );
        edge = graph.createEdge( 'A', 'A' );
        ok( graph.numEdges === 0 );

        // reflexive (allowed)
        graph = new GRAPH.Graph( false, {}, { allowReflexiveEdges: true });
        A = graph.createVertex( 'A' );
        edge = graph.createEdge( 'A', 'A' );
        // reflexive edges shouldn't mirror
        ok( graph.numEdges === 1 );
        ok( A.edges.A );
    });

    test( "Test graph.edges", function() {
        var graph = new GRAPH.Graph( false, nodeLinkData );
        ok( graph.edges().length === 6 );
        deepEqual( graph.edges( function( e ){ return e.source; }), [ 'A', 'A', 'B', 'B', 'C', 'C' ] );
        deepEqual( graph.edges({ source: 'A' }), [ graph.vertices.A.edges.B, graph.vertices.A.edges.C ] );

        graph = new GRAPH.Graph( true, nodeLinkData );
        ok( graph.edges().length === 3 );
        deepEqual( graph.edges( function( e ){ return e.source; }), [ 'A', 'A', 'B' ] );
        deepEqual( graph.edges({ source: 'A' }), [ graph.vertices.A.edges.B, graph.vertices.A.edges.C ] );
    });

    test( "Test graph.adjacent", function() {
        var graph = new GRAPH.Graph( true, nodeLinkData );
        deepEqual( graph.adjacent( graph.vertices.A ), [ graph.vertices.B, graph.vertices.C ] );
        deepEqual( graph.adjacent( graph.vertices.B ), [ graph.vertices.C ] );
        deepEqual( graph.adjacent( graph.vertices.C ), [] );
    });

    test( "Test graph.eachAdjacent", function() {
        var graph = new GRAPH.Graph( true, nodeLinkData );
        deepEqual( graph.eachAdjacent( graph.vertices.A, function( v, e ){ return v; }),
                  [ graph.vertices.B, graph.vertices.C ] );
    });

    // ------------------------------------------------------------------------ breadth first search
    test( "Empty BreadthFirstSearch", function(){
        var search = new GRAPH.BreadthFirstSearch();
        ok( search instanceof GRAPH.BreadthFirstSearch );
        ok( search.graph === undefined );
        ok( typeof search.processFns === 'object' );
        ok( typeof search.processFns.vertexEarly === 'function' );
        ok( typeof search.processFns.edge === 'function' );
        ok( typeof search.processFns.vertexLate === 'function' );
        ok( typeof search._cache === 'object' );
    });

    test( "BreadthFirstSearch on undirected graph", function(){
        var graph = new GRAPH.Graph( false, nodeLinkData ),
            bfs = new GRAPH.BreadthFirstSearch( graph );
        ok( bfs instanceof GRAPH.BreadthFirstSearch );
        ok( bfs.graph === graph );

        var search = bfs.search( 'A' ),
            tree = bfs.searchTree( 'A' );
        deepEqual( search, {
            discovered : { A: true, B: true, C: true },
            edges : [
                { source : 'A', target: 'B' },
                { source : 'A', target: 'C' }
            ]
        });
        ok( tree instanceof GRAPH.Graph );
        deepEqual( tree.vertices.A.toJSON(), graph.vertices.A.toJSON() );
        deepEqual( tree.eachVertex( function( v ){ return v.degree; }), [ 2, 0, 0 ] );

        deepEqual( bfs.search( 'B' ).edges, [
            { source : 'B', target: 'A' },
            { source : 'B', target: 'C' }
        ]);
        deepEqual( bfs.search( 'C' ).edges, [
            { source : 'C', target: 'A' },
            { source : 'C', target: 'B' }
        ]);
        ok( typeof bfs._cache.A === 'object' );
        deepEqual( Object.keys( bfs._cache ), [ 'A', 'B', 'C' ] );
    });

    test( "BreadthFirstSearch on directed graph", function(){
        var graph = new GRAPH.Graph( true, nodeLinkData ),
            bfs = new GRAPH.BreadthFirstSearch( graph );
        ok( bfs instanceof GRAPH.BreadthFirstSearch );
        ok( bfs.graph === graph );

        var search = bfs.search( 'A' ),
            tree = bfs.searchTree( 'A' );
        deepEqual( search, {
            discovered : { A: true, B: true, C: true },
            edges : [
                { source : 'A', target: 'B' },
                { source : 'A', target: 'C' }
            ]
        });
        ok( tree instanceof GRAPH.Graph );
        deepEqual( tree.vertices.A.toJSON(), graph.vertices.A.toJSON() );
        deepEqual( tree.eachVertex( function( v ){ return v.degree; }), [ 2, 0, 0 ] );

        deepEqual( bfs.search( 'B' ).edges, [
            { source : 'B', target: 'C' }
        ]);
        deepEqual( bfs.search( 'C' ).edges, []);
        ok( typeof bfs._cache.A === 'object' );
        deepEqual( Object.keys( bfs._cache ), [ 'A', 'B', 'C' ] );
    });

    // ------------------------------------------------------------------------ depth first search
    var DFSData = {
        vertices : [
            { name : 'A' },
            { name : 'B' },
            { name : 'C' },
            { name : 'D' },
            { name : 'E' },
            { name : 'F' }
        ],
        edges : [
            { source: 'A', target: 'B' },
            { source: 'B', target: 'C' },
            // confound it
            { source: 'A', target: 'C' },
            { source: 'C', target: 'D' },
            { source: 'A', target: 'E' },
            { source: 'E', target: 'F' },
            // confound it
            { source: 'F', target: 'A' }
        ]
    };

    test( "Empty DepthFirstSearch", function(){
        var search = new GRAPH.DepthFirstSearch();
        ok( search instanceof GRAPH.DepthFirstSearch );
        ok( search.graph === undefined );
        ok( typeof search.processFns === 'object' );
        ok( typeof search.processFns.vertexEarly === 'function' );
        ok( typeof search.processFns.edge === 'function' );
        ok( typeof search.processFns.vertexLate === 'function' );
        ok( typeof search._cache === 'object' );
    });

    test( "DepthFirstSearch on undirected graph", function(){
        var graph = new GRAPH.Graph( false, DFSData ),
            dfs = new GRAPH.DepthFirstSearch( graph );
        ok( dfs instanceof GRAPH.DepthFirstSearch );
        ok( dfs.graph === graph );

        var search = dfs.search( 'A' ),
            tree = dfs.searchTree( 'A' );
        deepEqual( search, {
            discovered : { A: true, B: true, C: true, D: true, E: true, F: true },
            edges : [
                { source : 'A', target: 'B' },
                { source : 'B', target: 'C' },
                { source : 'C', target: 'D' },
                { source : 'A', target: 'E' },
                { source : 'E', target: 'F' }
            ],
            entryTimes : { A: 0, B: 1, C: 2, D: 3, E: 7, F: 8 },
            exitTimes  : { A: 11, B: 6, C: 5, D: 4, E: 10, F: 9 }
        });
        ok( tree instanceof GRAPH.Graph );
        deepEqual( tree.vertices.A.toJSON(), graph.vertices.A.toJSON() );
        deepEqual( tree.eachVertex( function( v ){ return v.degree; }), [ 2, 1, 1, 0, 1, 0 ] );

        deepEqual( dfs.search( 'B' ).edges, [
            { source : 'B', target: 'A' },
            { source : 'A', target: 'C' },
            { source : 'C', target: 'D' },
            { source : 'A', target: 'E' },
            { source : 'E', target: 'F' }
        ]);

        ok( typeof dfs._cache.A === 'object' );
        deepEqual( Object.keys( dfs._cache ), [ 'A', 'B' ] );
    });

    test( "DepthFirstSearch on directed graph", function(){
        var graph = new GRAPH.Graph( true, DFSData ),
            dfs = new GRAPH.DepthFirstSearch( graph );
        ok( dfs instanceof GRAPH.DepthFirstSearch );
        ok( dfs.graph === graph );

        var search = dfs.search( 'A' ),
            tree = dfs.searchTree( 'A' );
        deepEqual( search, {
            discovered : { A: true, B: true, C: true, D: true, E: true, F: true },
            edges : [
                { source : 'A', target: 'B' },
                { source : 'B', target: 'C' },
                { source : 'C', target: 'D' },
                { source : 'A', target: 'E' },
                { source : 'E', target: 'F' }
            ],
            entryTimes : { A: 0, B: 1, C: 2, D: 3, E: 7, F: 8 },
            exitTimes  : { A: 11, B: 6, C: 5, D: 4, E: 10, F: 9 }
        });
        ok( tree instanceof GRAPH.Graph );
        deepEqual( tree.vertices.A.toJSON(), graph.vertices.A.toJSON() );
        deepEqual( tree.eachVertex( function( v ){ return v.degree; }), [ 2, 1, 1, 0, 1, 0 ] );

        deepEqual( dfs.search( 'B' ).edges, [
            { source : 'B', target: 'C' },
            { source : 'C', target: 'D' }
        ]);

        ok( typeof dfs._cache.A === 'object' );
        deepEqual( Object.keys( dfs._cache ), [ 'A', 'B' ] );
    });

    // ------------------------------------------------------------------------ components
//*/
    test( "weakComponents on undirected graph", function(){
        var graph = new GRAPH.Graph( false, {
            vertices : [
                { name : 'A' },
                { name : 'B' },
                { name : 'C' },
                { name : 'D' },
                { name : 'E' }
            ],
            edges : [
                { source: 'A', target: 'B' },
                { source: 'C', target: 'D' }
            ]
        });
        equal( graph.numEdges, 4 );
        var components = graph.weakComponents();
        equal( components.length, 3 );
    });

    test( "weakComponents on directed graph", function(){
        var graph, components;
        graph = new GRAPH.Graph( true, {
            vertices : [
                { name : 'A' },
                { name : 'B' },
                { name : 'C' },
                { name : 'D' },
                { name : 'E' }
            ],
            edges : [
                { source: 'A', target: 'B' },
                { source: 'D', target: 'C' }
            ]
        });
        equal( graph.numEdges, 2 );

        components = graph.weakComponents();
        equal( components.length, 3 );

        graph = new GRAPH.Graph( true, {
            vertices : [
                { name : 'A', data: 100 },
                { name : 'B', data: 200 },
                { name : 'C', data: 30 },
                { name : 'D', data: 40 },
                { name : 'E', data: 500 },
                { name : 'F', data: 600 },
                { name : 'G', data: 7 }
            ],
            edges : [
                { source: 'A', target: 'B' },
                { source: 'D', target: 'C' },
                { source: 'E', target: 'A' },
                { source: 'F', target: 'E' }
            ]
        });
        components = graph.weakComponents();
        equal( components.length, 3 );
        // data retained
        equal( components[0].vertices[0].data, 100 );

        equal( components[0].vertices.length, 4 );
        deepEqual( components[0].edges, [
            { source: 'A', target: 'B' },
            { source: 'E', target: 'A' },
            { source: 'F', target: 'E' }
        ]);

        equal( components[1].vertices.length, 2 );
        deepEqual( components[1].edges, [
            { source: 'D', target: 'C' }
        ]);

        deepEqual( components[2].vertices, [{ name : 'G', data: 7 }]);
        deepEqual( components[2].edges.length, 0 );
    });
});
