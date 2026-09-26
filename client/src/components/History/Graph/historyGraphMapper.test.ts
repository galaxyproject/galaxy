import { describe, expect, it } from "vitest";

import type { components } from "@/api/schema";

import { mapEdges, mapNodes, nodeKey } from "./historyGraphMapper";

type ApiGraphNode = components["schemas"]["GraphNode"];
type ApiGraphEdge = components["schemas"]["GraphEdge"];

// ── nodeKey ──

describe("nodeKey", () => {
    it("joins src and id with a colon", () => {
        expect(nodeKey({ src: "hda", id: "abc" })).toBe("hda:abc");
        expect(nodeKey({ src: "tool_request", id: "tr-1" })).toBe("tool_request:tr-1");
    });
});

// ── mapNodes — labels ──

describe("mapNodes labels", () => {
    it("prefixes hda label with hid when present", () => {
        const [node] = mapNodes([hda({ id: "a", hid: 7, name: "reads.fastq" })], []);
        expect(node!.label).toBe("7: reads.fastq");
    });

    it("omits hid when not set", () => {
        const [node] = mapNodes([hda({ id: "a", name: "reads.fastq" })], []);
        expect(node!.label).toBe("reads.fastq");
    });

    it("falls back to extension then to 'Dataset' for hda", () => {
        const [withExt] = mapNodes([hda({ id: "a", hid: 1, extension: "txt" })], []);
        expect(withExt!.label).toBe("1: txt");
        const [bare] = mapNodes([hda({ id: "b", hid: 2 })], []);
        expect(bare!.label).toBe("2: Dataset");
    });

    it("falls back to collection_type then to 'Collection' for hdca", () => {
        const [typed] = mapNodes([hdca({ id: "c", hid: 3, collection_type: "list" })], []);
        expect(typed!.label).toBe("3: list");
        const [bare] = mapNodes([hdca({ id: "d", hid: 4 })], []);
        expect(bare!.label).toBe("4: Collection");
    });

    it("uses tool_name when present, falling back to a shortened tool_id", () => {
        const nodes = mapNodes(
            [
                toolRequest({ id: "t1", tool_name: "BWA-MEM" }),
                toolRequest({ id: "t2", tool_id: "toolshed.g2.bx.psu.edu/repos/iuc/bwa_mem/bwa_mem/1.0" }),
                toolRequest({ id: "t3" }),
            ],
            [],
        );
        expect(nodes[0]!.label).toBe("1: BWA-MEM");
        expect(nodes[1]!.label).toBe("2: bwa_mem");
        expect(nodes[2]!.label).toBe("3: Tool");
    });

    it("assigns execution indices to tool_requests in input order, ignoring other nodes", () => {
        const nodes = mapNodes(
            [
                hda({ id: "a", hid: 1 }),
                toolRequest({ id: "t1", tool_name: "First" }),
                hdca({ id: "c", hid: 2 }),
                toolRequest({ id: "t2", tool_name: "Second" }),
            ],
            [],
        );
        expect(nodes[1]!.label).toBe("1: First");
        expect(nodes[3]!.label).toBe("2: Second");
    });
});

// ── mapNodes — badges, css, connectors ──

describe("mapNodes attributes", () => {
    it("emits extension as the badge for hda", () => {
        const [node] = mapNodes([hda({ id: "a", extension: "vcf" })], []);
        expect(node!.badge).toBe("vcf");
    });

    it("emits collection_type as the badge for hdca", () => {
        const [node] = mapNodes([hdca({ id: "c", collection_type: "list:paired" })], []);
        expect(node!.badge).toBe("list:paired");
    });

    it("emits no badge for tool_request", () => {
        const [node] = mapNodes([toolRequest({ id: "t" })], []);
        expect(node!.badge).toBeNull();
    });

    it("applies the per-src cssClass", () => {
        const [a, b, c] = mapNodes([hda({ id: "a" }), hdca({ id: "c" }), toolRequest({ id: "t" })], []);
        expect(a!.cssClass).toBe("node-dataset");
        expect(b!.cssClass).toBe("node-collection");
        expect(c!.cssClass).toBe("node-tool-request");
    });

    it("marks node as 'multiple' on the side that has any collection edge", () => {
        // Tool request t1 has one dataset_input edge from h1 and one collection_input from c1.
        // Merged input variant should be 'multiple'.
        const nodes = mapNodes(
            [hda({ id: "h1" }), hdca({ id: "c1" }), toolRequest({ id: "t1" })],
            [
                edge({ src: "hda", id: "h1" }, { src: "tool_request", id: "t1" }, "dataset_input"),
                edge({ src: "hdca", id: "c1" }, { src: "tool_request", id: "t1" }, "collection_input"),
            ],
        );
        const tr = nodes.find((n) => n.id === "tool_request:t1")!;
        expect(tr.inputConnector).toBe("multiple");
        expect(tr.outputConnector).toBeNull();
    });

    it("marks both connectors as null when no edges touch the node", () => {
        const [node] = mapNodes([hda({ id: "lonely" })], []);
        expect(node!.inputConnector).toBeNull();
        expect(node!.outputConnector).toBeNull();
    });

    it("summarises connection counts in body text for tool_request nodes", () => {
        const nodes = mapNodes(
            [hda({ id: "h1" }), hda({ id: "h2" }), toolRequest({ id: "t1" }), hda({ id: "out" })],
            [
                edge({ src: "hda", id: "h1" }, { src: "tool_request", id: "t1" }, "dataset_input"),
                edge({ src: "hda", id: "h2" }, { src: "tool_request", id: "t1" }, "dataset_input"),
                edge({ src: "tool_request", id: "t1" }, { src: "hda", id: "out" }, "dataset_output"),
            ],
        );
        const tr = nodes.find((n) => n.id === "tool_request:t1")!;
        expect(tr.data!.stateText).toBe("2 inputs, 1 output");
    });

    it("stores hid, src and itemId in node.data", () => {
        const [node] = mapNodes([hda({ id: "abc", hid: 12, name: "x" })], []);
        expect(node!.id).toBe("hda:abc");
        expect(node!.data!.src).toBe("hda");
        expect(node!.data!.itemId).toBe("abc");
    });
});

// ── mapEdges ──

describe("mapEdges", () => {
    it("encodes source/target with nodeKey and tags collection vs dataset edges", () => {
        const out = mapEdges([
            edge({ src: "hda", id: "h1" }, { src: "tool_request", id: "t1" }, "dataset_input"),
            edge({ src: "hdca", id: "c1" }, { src: "tool_request", id: "t1" }, "collection_input"),
        ]);
        expect(out[0]).toMatchObject({
            source: "hda:h1",
            target: "tool_request:t1",
            cssClass: "edge-dataset",
            sourceVariant: "single",
            targetVariant: "single",
        });
        expect(out[1]).toMatchObject({
            source: "hdca:c1",
            target: "tool_request:t1",
            cssClass: "edge-collection",
            sourceVariant: "multiple",
            targetVariant: "multiple",
        });
    });

    it("assigns stable, unique edge ids", () => {
        const out = mapEdges([
            edge({ src: "hda", id: "h1" }, { src: "tool_request", id: "t1" }, "dataset_input"),
            edge({ src: "tool_request", id: "t1" }, { src: "hda", id: "h2" }, "dataset_output"),
        ]);
        expect(out.map((e) => e.id)).toEqual(["e0", "e1"]);
    });
});

// ── helpers ──

function hda(overrides: Partial<ApiGraphNode>): ApiGraphNode {
    return { id: "x", src: "hda", ...overrides };
}

function hdca(overrides: Partial<ApiGraphNode>): ApiGraphNode {
    return { id: "x", src: "hdca", ...overrides };
}

function toolRequest(overrides: Partial<ApiGraphNode>): ApiGraphNode {
    return { id: "x", src: "tool_request", ...overrides };
}

function edge(
    source: { src: ApiGraphNode["src"]; id: string },
    target: { src: ApiGraphNode["src"]; id: string },
    type: ApiGraphEdge["type"],
): ApiGraphEdge {
    return { source, target, type };
}
