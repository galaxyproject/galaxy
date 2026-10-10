import { describe, expect, it } from "vitest";

import { parseInvocation } from "./parseInvocation";

const INVOCATION = {
    id: "invocation_id_1",
    history_id: "history_id_1",
    inputs: [
        {
            label: "input_1",
            id: "input_id_1",
        },
        {
            label: "input_2",
            id: "input_id_2",
        },
        {
            label: "input_3",
            id: "input_id_3",
        },
        {
            label: "input_collection_1",
            id: "input_collection_id_1",
            src: "hdca",
        },
    ],
    outputs: {
        output_1: {
            id: "output_id_1",
        },
    },
    output_collections: {
        output_2: {
            id: "output_id_2",
        },
    },
    steps: [
        {
            workflow_step_label: "workflow_step_1",
            job_id: "job_id_1",
        },
        {
            workflow_step_label: "workflow_step_2",
            implicit_collection_jobs_id: "implicit_id_2",
            job_id: "job_id_2",
        },
    ],
};

const STORED_WORKFLOW_ID = "workflow_id_1";

function parse(directiveName, attributes = {}) {
    return parseInvocation(INVOCATION, STORED_WORKFLOW_ID, directiveName, attributes);
}

describe("parseInvocation", () => {
    it("attaches the invocation to the parsed attributes", () => {
        expect(parse("").invocation).toBe(INVOCATION);
    });

    it("links history_link to the invocation's history", () => {
        expect(parse("history_link").history_id).toBe("history_id_1");
    });

    it.each(["workflow_display", "workflow_image", "workflow_license"])(
        "links %s to the stored workflow",
        (directiveName) => {
            expect(parse(directiveName).workflow_id).toBe("workflow_id_1");
        },
    );

    it("resolves a labeled dataset input to its history dataset", () => {
        expect(parse("history_dataset_display", { input: "input_3" }).history_dataset_id).toBe("input_id_3");
    });

    it("resolves a labeled collection input to its collection, even where a dataset is required", () => {
        const result = parse("history_dataset_as_image", { input: "input_collection_1" });

        expect(result.history_dataset_collection_id).toBe("input_collection_id_1");
        expect(result.history_dataset_id).toBeUndefined();
    });

    it("leaves the history dataset unset for an unknown output label", () => {
        expect(parse("history_dataset_display", { output: "unavailable_output" }).history_dataset_id).toBeUndefined();
    });

    it("resolves a labeled output collection to its collection", () => {
        expect(parse("history_dataset_collection_display", { output: "output_2" }).history_dataset_collection_id).toBe(
            "output_id_2",
        );
    });

    it("resolves a labeled step to its job", () => {
        expect(parse("", { step: "workflow_step_1" }).job_id).toBe("job_id_1");
    });

    it("resolves a labeled mapped-over step to its implicit collection jobs and job", () => {
        const result = parse("", { step: "workflow_step_2" });

        expect(result.implicit_collection_jobs_id).toBe("implicit_id_2");
        expect(result.job_id).toBe("job_id_2");
    });
});
