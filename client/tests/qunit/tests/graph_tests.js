/* global QUnit */
import testApp from "../test-app";
import GRAPH from "utils/graph";

QUnit.module("utils/graph.js library tests", {
    beforeEach: function () {
        testApp.create();
    },
    afterEach: function () {
        testApp.destroy();
    },
});

///*
function testEmptyObject(assert, o) {
    assert.ok(typeof o === "object");
    assert.ok(Object.keys(o).length === 0);
}

// ------------------------------------------------------------------------ vertices
QUnit.test("Empty vertex construction", function (assert) {
    var vert = new GRAPH.Vertex();
    assert.ok(vert instanceof GRAPH.Vertex);
    assert.ok(vert.name === "(unnamed)");
    assert.ok(vert.data === null);
    testEmptyObject(assert, vert.edges);
    assert.ok(vert.degree === 0);
    assert.ok(vert + "" === "Vertex((unnamed))");
    assert.deepEqual(vert.toJSON(), { name: "(unnamed)", data: null });
});

QUnit.test("Vertex construction", function (assert) {
    var vert = new GRAPH.Vertex("blah", { blorp: 1, bleep: 2 });
    assert.ok(vert instanceof GRAPH.Vertex);
    assert.ok(vert.name === "blah");
    assert.deepEqual(vert.data, { blorp: 1, bleep: 2 });
    testEmptyObject(assert, vert.edges);
    assert.ok(vert.degree === 0);
    assert.ok(vert + "" === "Vertex(blah)");
    assert.deepEqual(vert.toJSON(), { name: "blah", data: { blorp: 1, bleep: 2 } });
});

// ------------------------------------------------------------------------ edges
QUnit.test("Empty edge construction", function (assert) {
    var edge = new GRAPH.Edge();
    assert.ok(edge instanceof GRAPH.Edge);
    assert.ok(edge.source === null);
    assert.ok(edge.target === null);
    assert.ok(edge.data === null);
    assert.ok(edge + "" === "null->null");
    assert.deepEqual(edge.toJSON(), { source: null, target: null });
});

QUnit.test("Edge construction", function (assert) {
    var edge = new GRAPH.Edge("A", "B", { one: 1, two: 2 });
    assert.ok(edge instanceof GRAPH.Edge);
    assert.ok(edge.source === "A");
    assert.ok(edge.target === "B");
    assert.deepEqual(edge.data, { one: 1, two: 2 });
    assert.ok(edge + "" === "A->B");
    assert.deepEqual(edge.toJSON(), { source: "A", target: "B", data: { one: 1, two: 2 } });
});

// ------------------------------------------------------------------------ graphs
function testEmptyGraph(assert, graph) {
    assert.ok(graph instanceof GRAPH.Graph);
    testEmptyObject(assert, graph.vertices);
    assert.ok(graph.numEdges === 0);
}

QUnit.test("Empty graph construction", function (assert) {
    var graph = new GRAPH.Graph();

    assert.ok(graph.directed === false);
    assert.ok(graph.allowReflexiveEdges === false);

    testEmptyGraph(assert, graph);
});

QUnit.test("Bad data graph construction", function (assert) {
    var graph = new GRAPH.Graph(false, {});
    testEmptyGraph(assert, graph);

    graph = new GRAPH.Graph(false, null);
    testEmptyGraph(assert, graph);
});

QUnit.test("Test directed and options", function (assert) {
    var graph = new GRAPH.Graph(true, {}, { allowReflexiveEdges: true });

    assert.ok(graph.directed);
    assert.ok(graph.allowReflexiveEdges);

    testEmptyGraph(assert, graph);
});

function testSampleDirectedGraph(assert, graph) {
    assert.ok(!graph.directed);

    assert.ok(Object.keys(graph.vertices).length === 3);
    assert.ok(graph.vertices.A instanceof GRAPH.Vertex);
    assert.ok(graph.vertices.B instanceof GRAPH.Vertex);
    assert.ok(graph.vertices.C instanceof GRAPH.Vertex);

    assert.deepEqual(Object.keys(graph.vertices.A.edges), ["B", "C"]);
    assert.deepEqual(Object.keys(graph.vertices.B.edges), ["A", "C"]);
    assert.deepEqual(Object.keys(graph.vertices.C.edges), ["A", "B"]);

    assert.ok(graph.vertices.A.degree === 2);
    assert.ok(graph.vertices.B.degree === 2);
    assert.ok(graph.vertices.C.degree === 2);

    assert.deepEqual(graph.vertices.A.edges.B.toJSON(), { source: "A", target: "B" });
    assert.deepEqual(graph.vertices.A.edges.C.toJSON(), { source: "A", target: "C" });
    assert.deepEqual(graph.vertices.B.edges.A.toJSON(), { source: "B", target: "A" });
    assert.deepEqual(graph.vertices.B.edges.C.toJSON(), { source: "B", target: "C" });
    assert.deepEqual(graph.vertices.C.edges.A.toJSON(), { source: "C", target: "A" });
    assert.deepEqual(graph.vertices.C.edges.B.toJSON(), { source: "C", target: "B" });

    assert.ok(graph.numEdges === 6);
}

function testSampleNonDirectedGraph(assert, graph) {
    assert.ok(graph.directed);

    assert.ok(Object.keys(graph.vertices).length === 3);
    assert.ok(graph.vertices.A instanceof GRAPH.Vertex);
    assert.ok(graph.vertices.B instanceof GRAPH.Vertex);
    assert.ok(graph.vertices.C instanceof GRAPH.Vertex);

    assert.deepEqual(Object.keys(graph.vertices.A.edges), ["B", "C"]);
    assert.deepEqual(Object.keys(graph.vertices.B.edges), ["C"]);
    assert.deepEqual(Object.keys(graph.vertices.C.edges), []);

    assert.ok(graph.vertices.A.degree === 2);
    assert.ok(graph.vertices.B.degree === 1);
    assert.ok(graph.vertices.C.degree === 0);

    assert.deepEqual(graph.vertices.A.edges.B.toJSON(), { source: "A", target: "B" });
    assert.deepEqual(graph.vertices.A.edges.C.toJSON(), { source: "A", target: "C" });
    assert.deepEqual(graph.vertices.B.edges.C.toJSON(), { source: "B", target: "C" });

    assert.ok(graph.numEdges === 3);
}

var nodeLinkData = {
    nodes: [
        { name: "A", data: 100 },
        { name: "B", data: 200 },
        { name: "C", data: 300 },
    ],
    links: [
        { source: 0, target: 1 },
        { source: 0, target: 2 },
        { source: 1, target: 2 },
    ],
};

QUnit.test("Test nodes and links data input on *non-directed* graph", function (assert) {
    var graph = new GRAPH.Graph(false, nodeLinkData);
    testSampleDirectedGraph(assert, graph);
});

QUnit.test("Test nodes and links data input on *directed* graph", function (assert) {
    var graph = new GRAPH.Graph(true, nodeLinkData);
    testSampleNonDirectedGraph(assert, graph);
});

var vertexEdgeData = {
    vertices: [
        { name: "A", data: 100 },
        { name: "B", data: 200 },
        { name: "C", data: 300 },
    ],
    edges: [
        { source: "A", target: "B" },
        { source: "A", target: "C" },
        { source: "B", target: "C" },
    ],
};

QUnit.test("Test vertex and edge data input on *non-directed* graph", function (assert) {
    var graph = new GRAPH.Graph(false, vertexEdgeData);
    testSampleDirectedGraph(assert, graph);
});

QUnit.test("Test vertex and edge data input on *directed* graph", function (assert) {
    var graph = new GRAPH.Graph(true, vertexEdgeData);
    testSampleNonDirectedGraph(assert, graph);
});

QUnit.test("Test vertex eachEdge", function (assert) {
    var graph = new GRAPH.Graph(false, nodeLinkData);
    assert.ok(typeof graph.vertices.A.eachEdge === "function");
    assert.deepEqual(
        graph.vertices.A.eachEdge(function (e) {
            return e.target;
        }),
        ["B", "C"]
    );
    assert.ok(graph.vertices.A.eachEdge({ target: "B" }).length === 1);
});

QUnit.test("Test graph eachVertex", function (assert) {
    var graph = new GRAPH.Graph(true, nodeLinkData);
    assert.ok(typeof graph.eachVertex === "function");
    assert.deepEqual(
        graph.eachVertex(function (v) {
            return { n: v.name, d: v.degree };
        }),
        [
            { n: "A", d: 2 },
            { n: "B", d: 1 },
            { n: "C", d: 0 },
        ]
    );
    assert.ok(graph.eachVertex({ degree: 2 })[0] === graph.vertices.A);
});

QUnit.test("Test createVertex", function (assert) {
    var graph = new GRAPH.Graph();
    var vert1 = graph.createVertex("A", { blah: 1 });
    assert.ok(vert1 instanceof GRAPH.Vertex);
    assert.ok(vert1 === graph.vertices.A);
    assert.ok(graph.createVertex("A", { blah: 1 }) === vert1);
});

QUnit.test("Test createEdge", function (assert) {
    var graph, A, B, edge;

    graph = new GRAPH.Graph();
    A = graph.createVertex("A");
    B = graph.createVertex("B");
    edge = graph.createEdge("A", "B");
    assert.ok(edge instanceof GRAPH.Edge);
    assert.ok(A.degree === 1);
    assert.ok(B.degree === 1);
    assert.ok(A.edges.B);
    assert.ok(B.edges.A);
    assert.ok(graph.numEdges === 2);

    // bad target
    graph = new GRAPH.Graph();
    A = graph.createVertex("A");
    B = graph.createVertex("B");
    edge = graph.createEdge("A", "C");
    assert.ok(edge === null);
    assert.ok(A.degree === 0);
    assert.ok(B.degree === 0);
    assert.ok(!A.edges.B);
    assert.ok(!B.edges.A);
    assert.ok(graph.numEdges === 0);

    // bad source
    graph = new GRAPH.Graph();
    A = graph.createVertex("A");
    B = graph.createVertex("B");
    edge = graph.createEdge("C", "A");
    assert.ok(graph.numEdges === 0);

    // reflexive
    graph = new GRAPH.Graph();
    A = graph.createVertex("A");
    B = graph.createVertex("B");
    edge = graph.createEdge("A", "A");
    assert.ok(graph.numEdges === 0);

    // reflexive (allowed)
    graph = new GRAPH.Graph(false, {}, { allowReflexiveEdges: true });
    A = graph.createVertex("A");
    edge = graph.createEdge("A", "A");
    // reflexive edges shouldn't mirror
    assert.ok(graph.numEdges === 1);
    assert.ok(A.edges.A);
});

QUnit.test("Test graph.edges", function (assert) {
    var graph = new GRAPH.Graph(false, nodeLinkData);
    assert.ok(graph.edges().length === 6);
    assert.deepEqual(
        graph.edges(function (e) {
            return e.source;
        }),
        ["A", "A", "B", "B", "C", "C"]
    );
    assert.deepEqual(graph.edges({ source: "A" }), [graph.vertices.A.edges.B, graph.vertices.A.edges.C]);

    graph = new GRAPH.Graph(true, nodeLinkData);
    assert.ok(graph.edges().length === 3);
    assert.deepEqual(
        graph.edges(function (e) {
            return e.source;
        }),
        ["A", "A", "B"]
    );
    assert.deepEqual(graph.edges({ source: "A" }), [graph.vertices.A.edges.B, graph.vertices.A.edges.C]);
});

QUnit.test("Test graph.adjacent", function (assert) {
    var graph = new GRAPH.Graph(true, nodeLinkData);
    assert.deepEqual(graph.adjacent(graph.vertices.A), [graph.vertices.B, graph.vertices.C]);
    assert.deepEqual(graph.adjacent(graph.vertices.B), [graph.vertices.C]);
    assert.deepEqual(graph.adjacent(graph.vertices.C), []);
});

QUnit.test("Test graph.eachAdjacent", function (assert) {
    var graph = new GRAPH.Graph(true, nodeLinkData);
    assert.deepEqual(
        graph.eachAdjacent(graph.vertices.A, function (v, e) {
            return v;
        }),
        [graph.vertices.B, graph.vertices.C]
    );
});

// ------------------------------------------------------------------------ breadth first search
QUnit.test("Empty BreadthFirstSearch", function (assert) {
    var search = new GRAPH.BreadthFirstSearch();
    assert.ok(search instanceof GRAPH.BreadthFirstSearch);
    assert.ok(search.graph === undefined);
    assert.ok(typeof search.processFns === "object");
    assert.ok(typeof search.processFns.vertexEarly === "function");
    assert.ok(typeof search.processFns.edge === "function");
    assert.ok(typeof search.processFns.vertexLate === "function");
    assert.ok(typeof search._cache === "object");
});

QUnit.test("BreadthFirstSearch on undirected graph", function (assert) {
    var graph = new GRAPH.Graph(false, nodeLinkData),
        bfs = new GRAPH.BreadthFirstSearch(graph);
    assert.ok(bfs instanceof GRAPH.BreadthFirstSearch);
    assert.ok(bfs.graph === graph);

    var search = bfs.search("A"),
        tree = bfs.searchTree("A");
    assert.deepEqual(search, {
        discovered: { A: true, B: true, C: true },
        edges: [
            { source: "A", target: "B" },
            { source: "A", target: "C" },
        ],
    });
    assert.ok(tree instanceof GRAPH.Graph);
    assert.deepEqual(tree.vertices.A.toJSON(), graph.vertices.A.toJSON());
    assert.deepEqual(
        tree.eachVertex(function (v) {
            return v.degree;
        }),
        [2, 0, 0]
    );

    assert.deepEqual(bfs.search("B").edges, [
        { source: "B", target: "A" },
        { source: "B", target: "C" },
    ]);
    assert.deepEqual(bfs.search("C").edges, [
        { source: "C", target: "A" },
        { source: "C", target: "B" },
    ]);
    assert.ok(typeof bfs._cache.A === "object");
    assert.deepEqual(Object.keys(bfs._cache), ["A", "B", "C"]);
});

QUnit.test("BreadthFirstSearch on directed graph", function (assert) {
    var graph = new GRAPH.Graph(true, nodeLinkData),
        bfs = new GRAPH.BreadthFirstSearch(graph);
    assert.ok(bfs instanceof GRAPH.BreadthFirstSearch);
    assert.ok(bfs.graph === graph);

    var search = bfs.search("A"),
        tree = bfs.searchTree("A");
    assert.deepEqual(search, {
        discovered: { A: true, B: true, C: true },
        edges: [
            { source: "A", target: "B" },
            { source: "A", target: "C" },
        ],
    });
    assert.ok(tree instanceof GRAPH.Graph);
    assert.deepEqual(tree.vertices.A.toJSON(), graph.vertices.A.toJSON());
    assert.deepEqual(
        tree.eachVertex(function (v) {
            return v.degree;
        }),
        [2, 0, 0]
    );

    assert.deepEqual(bfs.search("B").edges, [{ source: "B", target: "C" }]);
    assert.deepEqual(bfs.search("C").edges, []);
    assert.ok(typeof bfs._cache.A === "object");
    assert.deepEqual(Object.keys(bfs._cache), ["A", "B", "C"]);
});

// ------------------------------------------------------------------------ depth first search
var DFSData = {
    vertices: [{ name: "A" }, { name: "B" }, { name: "C" }, { name: "D" }, { name: "E" }, { name: "F" }],
    edges: [
        { source: "A", target: "B" },
        { source: "B", target: "C" },
        // confound it
        { source: "A", target: "C" },
        { source: "C", target: "D" },
        { source: "A", target: "E" },
        { source: "E", target: "F" },
        // confound it
        { source: "F", target: "A" },
    ],
};

QUnit.test("Empty DepthFirstSearch", function (assert) {
    var search = new GRAPH.DepthFirstSearch();
    assert.ok(search instanceof GRAPH.DepthFirstSearch);
    assert.ok(search.graph === undefined);
    assert.ok(typeof search.processFns === "object");
    assert.ok(typeof search.processFns.vertexEarly === "function");
    assert.ok(typeof search.processFns.edge === "function");
    assert.ok(typeof search.processFns.vertexLate === "function");
    assert.ok(typeof search._cache === "object");
});

QUnit.test("DepthFirstSearch on undirected graph", function (assert) {
    var graph = new GRAPH.Graph(false, DFSData),
        dfs = new GRAPH.DepthFirstSearch(graph);
    assert.ok(dfs instanceof GRAPH.DepthFirstSearch);
    assert.ok(dfs.graph === graph);

    var search = dfs.search("A"),
        tree = dfs.searchTree("A");
    assert.deepEqual(search, {
        discovered: { A: true, B: true, C: true, D: true, E: true, F: true },
        edges: [
            { source: "A", target: "B" },
            { source: "B", target: "C" },
            { source: "C", target: "D" },
            { source: "A", target: "E" },
            { source: "E", target: "F" },
        ],
        entryTimes: { A: 0, B: 1, C: 2, D: 3, E: 7, F: 8 },
        exitTimes: { A: 11, B: 6, C: 5, D: 4, E: 10, F: 9 },
    });
    assert.ok(tree instanceof GRAPH.Graph);
    assert.deepEqual(tree.vertices.A.toJSON(), graph.vertices.A.toJSON());
    assert.deepEqual(
        tree.eachVertex(function (v) {
            return v.degree;
        }),
        [2, 1, 1, 0, 1, 0]
    );

    assert.deepEqual(dfs.search("B").edges, [
        { source: "B", target: "A" },
        { source: "A", target: "C" },
        { source: "C", target: "D" },
        { source: "A", target: "E" },
        { source: "E", target: "F" },
    ]);

    assert.ok(typeof dfs._cache.A === "object");
    assert.deepEqual(Object.keys(dfs._cache), ["A", "B"]);
});

QUnit.test("DepthFirstSearch on directed graph", function (assert) {
    var graph = new GRAPH.Graph(true, DFSData),
        dfs = new GRAPH.DepthFirstSearch(graph);
    assert.ok(dfs instanceof GRAPH.DepthFirstSearch);
    assert.ok(dfs.graph === graph);

    var search = dfs.search("A"),
        tree = dfs.searchTree("A");
    assert.deepEqual(search, {
        discovered: { A: true, B: true, C: true, D: true, E: true, F: true },
        edges: [
            { source: "A", target: "B" },
            { source: "B", target: "C" },
            { source: "C", target: "D" },
            { source: "A", target: "E" },
            { source: "E", target: "F" },
        ],
        entryTimes: { A: 0, B: 1, C: 2, D: 3, E: 7, F: 8 },
        exitTimes: { A: 11, B: 6, C: 5, D: 4, E: 10, F: 9 },
    });
    assert.ok(tree instanceof GRAPH.Graph);
    assert.deepEqual(tree.vertices.A.toJSON(), graph.vertices.A.toJSON());
    assert.deepEqual(
        tree.eachVertex(function (v) {
            return v.degree;
        }),
        [2, 1, 1, 0, 1, 0]
    );

    assert.deepEqual(dfs.search("B").edges, [
        { source: "B", target: "C" },
        { source: "C", target: "D" },
    ]);

    assert.ok(typeof dfs._cache.A === "object");
    assert.deepEqual(Object.keys(dfs._cache), ["A", "B"]);
});

// ------------------------------------------------------------------------ components
//*/
QUnit.test("weakComponents on undirected graph", function (assert) {
    var graph = new GRAPH.Graph(false, {
        vertices: [{ name: "A" }, { name: "B" }, { name: "C" }, { name: "D" }, { name: "E" }],
        edges: [
            { source: "A", target: "B" },
            { source: "C", target: "D" },
        ],
    });
    assert.equal(graph.numEdges, 4);
    var components = graph.weakComponents();
    assert.equal(components.length, 3);
});

QUnit.test("weakComponents on directed graph", function (assert) {
    var graph, components;
    graph = new GRAPH.Graph(true, {
        vertices: [{ name: "A" }, { name: "B" }, { name: "C" }, { name: "D" }, { name: "E" }],
        edges: [
            { source: "A", target: "B" },
            { source: "D", target: "C" },
        ],
    });
    assert.equal(graph.numEdges, 2);

    components = graph.weakComponents();
    assert.equal(components.length, 3);

    graph = new GRAPH.Graph(true, {
        vertices: [
            { name: "A", data: 100 },
            { name: "B", data: 200 },
            { name: "C", data: 30 },
            { name: "D", data: 40 },
            { name: "E", data: 500 },
            { name: "F", data: 600 },
            { name: "G", data: 7 },
        ],
        edges: [
            { source: "A", target: "B" },
            { source: "D", target: "C" },
            { source: "E", target: "A" },
            { source: "F", target: "E" },
        ],
    });
    components = graph.weakComponents();
    assert.equal(components.length, 3);
    // data retained
    assert.equal(components[0].vertices[0].data, 100);

    assert.equal(components[0].vertices.length, 4);
    assert.deepEqual(components[0].edges, [
        { source: "A", target: "B" },
        { source: "E", target: "A" },
        { source: "F", target: "E" },
    ]);

    assert.equal(components[1].vertices.length, 2);
    assert.deepEqual(components[1].edges, [{ source: "D", target: "C" }]);

    assert.deepEqual(components[2].vertices, [{ name: "G", data: 7 }]);
    assert.deepEqual(components[2].edges.length, 0);
});
