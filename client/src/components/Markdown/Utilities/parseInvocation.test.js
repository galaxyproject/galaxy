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
    ],
    outputs: {
        output_1: {
            id: "output_id_1",
        },
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

describe("parseInvocation.ts", () => {
    describe("parseInvocation", () => {
        it("populate args with invocation details", () => {
            expect(parseInvocation(INVOCATION, STORED_WORKFLOW_ID, "history_link", {}).history_id).toBe("history_id_1");
            expect(parseInvocation(INVOCATION, STORED_WORKFLOW_ID, "workflow_display", {}).workflow_id).toBe(
                "workflow_id_1"
            );
            expect(parseInvocation(INVOCATION, STORED_WORKFLOW_ID, "workflow_image", {}).workflow_id).toBe(
                "workflow_id_1"
            );
            expect(parseInvocation(INVOCATION, STORED_WORKFLOW_ID, "workflow_license", {}).workflow_id).toBe(
                "workflow_id_1"
            );
            expect(
                parseInvocation(INVOCATION, STORED_WORKFLOW_ID, "history_dataset_display", {
                    input: "input_3",
                }).history_dataset_id
            ).toBe("input_id_3");
            expect(
                parseInvocation(INVOCATION, STORED_WORKFLOW_ID, "history_dataset_display", {
                    output: "unavailable_output",
                }).history_dataset_id
            ).toBeUndefined();
            expect(
                parseInvocation(INVOCATION, STORED_WORKFLOW_ID, "history_dataset_collection_display", {
                    output: "output_2",
                }).history_dataset_collection_id
            ).toBe("output_id_2");
            expect(
                parseInvocation(INVOCATION, STORED_WORKFLOW_ID, "", {
                    step: "workflow_step_1",
                }).job_id
            ).toBe("job_id_1");
            expect(
                parseInvocation(INVOCATION, STORED_WORKFLOW_ID, "", {
                    step: "workflow_step_2",
                }).implicit_collection_jobs_id
            ).toBe("implicit_id_2");
            expect(parseInvocation(INVOCATION, STORED_WORKFLOW_ID, "", {}).invocation.id).toBe("invocation_id_1");
        });
    });
});
