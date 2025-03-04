import { parseInvocation } from "./parseInvocation";

const INVOCATION = {
    id: "invoction_id",
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

describe("parseInvocation.ts", () => {
    describe("parseInvocation", () => {
        it("populate args with invocation details", () => {
            expect(
                parseInvocation(INVOCATION, {
                    input: "input_3",
                }).history_target_id
            ).toBe("input_id_3");
            expect(
                parseInvocation(INVOCATION, {
                    output: "unavailable_output",
                }).history_target_id
            ).toBeUndefined();
            expect(
                parseInvocation(INVOCATION, {
                    output: "output_2",
                }).history_target_id
            ).toBe("output_id_2");
            expect(
                parseInvocation(INVOCATION, {
                    step: "workflow_step_1",
                }).job_id
            ).toBe("job_id_1");
            expect(
                parseInvocation(INVOCATION, {
                    step: "workflow_step_2",
                }).implicit_collection_jobs_id
            ).toBe("implicit_id_2");
            expect(parseInvocation(INVOCATION, {}).invocation.id).toBe("invoction_id");
        });
    });
});
