import { describe, expect, it } from "vitest";

import type { DatatypeConverter } from "@/api/datatypes";
import { DatatypesMapperModel } from "@/components/Datatypes/model";
import type { Tool, ToolDataInput } from "@/stores/toolStore";

import { matchInteractiveTools } from "./interactiveToolMatching";

const mapper = new DatatypesMapperModel({
    datatypes: ["bed", "fasta", "interval", "tabular", "txt"],
    datatypes_mapping: {
        ext_to_class_name: {
            bed: "galaxy.datatypes.interval.Bed",
            fasta: "galaxy.datatypes.sequence.Fasta",
            interval: "galaxy.datatypes.interval.Interval",
            tabular: "galaxy.datatypes.tabular.Tabular",
            txt: "galaxy.datatypes.data.Text",
        },
        class_to_classes: {
            "galaxy.datatypes.interval.Bed": {
                "galaxy.datatypes.interval.Bed": true,
                "galaxy.datatypes.interval.Interval": true,
                "galaxy.datatypes.tabular.Tabular": true,
                "galaxy.datatypes.data.Text": true,
                "galaxy.datatypes.data.Data": true,
            },
            "galaxy.datatypes.sequence.Fasta": {
                "galaxy.datatypes.sequence.Fasta": true,
                "galaxy.datatypes.data.Text": true,
                "galaxy.datatypes.data.Data": true,
            },
            "galaxy.datatypes.interval.Interval": {
                "galaxy.datatypes.interval.Interval": true,
                "galaxy.datatypes.tabular.Tabular": true,
                "galaxy.datatypes.data.Text": true,
                "galaxy.datatypes.data.Data": true,
            },
            "galaxy.datatypes.tabular.Tabular": {
                "galaxy.datatypes.tabular.Tabular": true,
                "galaxy.datatypes.data.Text": true,
                "galaxy.datatypes.data.Data": true,
            },
            "galaxy.datatypes.data.Text": {
                "galaxy.datatypes.data.Text": true,
                "galaxy.datatypes.data.Data": true,
            },
        },
    },
});

const converters: DatatypeConverter[] = [
    { source: "fasta", target: "tabular", tool_id: "CONVERTER_fasta_to_tabular" },
    { source: "interval", target: "fasta", tool_id: "CONVERTER_interval_to_fasta" },
];

function dataInput(name: string | null, extensions: string[]): ToolDataInput {
    return { name, extensions, multiple: false, type: "data", collection_type: null };
}

function tool(id: string, dataInputs: ToolDataInput[], name = id): Tool {
    return { id, name, version: "1.0", data_inputs: dataInputs } as Tool;
}

function summary(extension: string, tools: Tool[]) {
    return matchInteractiveTools(tools, extension, mapper, converters).map((result) => [
        result.tool.id,
        result.match,
        result.inputName,
    ]);
}

describe("matchInteractiveTools", () => {
    it("matches a direct format and a subtype directly", () => {
        const tools = [tool("tabular_tool", [dataInput("infile", ["tabular"])])];
        expect(summary("tabular", tools)).toEqual([["tabular_tool", "direct", "infile"]]);
        expect(summary("bed", tools)).toEqual([["tabular_tool", "direct", "infile"]]);
    });

    it("matches through a converter of the dataset's datatype", () => {
        const tools = [tool("tabular_tool", [dataInput("infile", ["tabular"])])];
        expect(summary("fasta", tools)).toEqual([["tabular_tool", "converted", "infile"]]);
    });

    it("matches through a converter registered on a parent datatype", () => {
        const tools = [tool("fasta_tool", [dataInput("infile", ["fasta"])])];
        expect(summary("bed", tools)).toEqual([["fasta_tool", "converted", "infile"]]);
    });

    it("matches an input that accepts any datatype as generic", () => {
        const tools = [tool("any_tool", [dataInput("user_inputs_0|infile", ["data"])])];
        expect(summary("txt", tools)).toEqual([["any_tool", "generic", "user_inputs_0|infile"]]);
    });

    it("leaves out tools without an accepting input", () => {
        const tools = [tool("fasta_tool", [dataInput("infile", ["fasta"])]), tool("no_inputs", [])];
        expect(summary("txt", tools)).toEqual([]);
    });

    it("leaves out tools without listed data inputs", () => {
        const tools = [{ id: "unlisted", name: "unlisted", version: "1.0" } as Tool];
        expect(summary("tabular", tools)).toEqual([]);
    });

    it("does not match unknown datatypes", () => {
        const tools = [tool("unknown_input", [dataInput("infile", ["not_a_datatype"])])];
        expect(summary("tabular", tools)).toEqual([]);
        expect(summary("not_a_datatype_either", [tool("tabular_tool", [dataInput("infile", ["tabular"])])])).toEqual(
            [],
        );
    });

    it("prefers an input the form can prefill on an equal match", () => {
        const tools = [tool("tie", [dataInput(null, ["tabular"]), dataInput("prefillable", ["tabular"])])];
        expect(summary("tabular", tools)).toEqual([["tie", "direct", "prefillable"]]);
    });

    it("prefers a better match over a prefillable input", () => {
        const tools = [tool("rank", [dataInput("any", ["data"]), dataInput(null, ["tabular"])])];
        expect(summary("tabular", tools)).toEqual([["rank", "direct", null]]);
    });

    it("sorts by match, then by name", () => {
        const tools = [
            tool("generic", [dataInput("infile", ["data"])], "Alpha"),
            tool("converted", [dataInput("infile", ["fasta"])], "beta"),
            tool("direct_b", [dataInput("infile", ["bed"])], "Delta"),
            tool("direct_a", [dataInput("infile", ["interval"])], "charlie"),
        ];
        expect(summary("bed", tools).map(([id]) => id)).toEqual(["direct_a", "direct_b", "converted", "generic"]);
    });
});
