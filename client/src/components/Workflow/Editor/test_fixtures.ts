import type { UseElementBoundingReturn } from "@vueuse/core";
import { reactive, toRefs } from "vue";

import type { InputTerminalSource, NewStep, Steps } from "@/stores/workflowStepStore";

import _advancedSteps from "./test-data/parameter_steps.json";
import _simpleSteps from "./test-data/simple_steps.json";

const _mockOffset = toRefs(reactive({ top: 0, left: 0, bottom: 10, right: 10, width: 100, height: 100, x: 0, y: 0 }));
 
export const mockOffset: UseElementBoundingReturn = { ..._mockOffset, update: () => {} };

export const simpleSteps = _simpleSteps as Steps;
export const advancedSteps = _advancedSteps as Steps;

/** Creates a mock step position for testing (satisfies UseElementBoundingReturn shape) */
export function createMockStepPosition(width: number, height: number) {
    return {
        width,
        height,
        top: 0,
        left: 0,
        bottom: height,
        right: width,
        x: 0,
        y: 0,
        update: () => {},
    };
}

/** Creates a minimal workflow step for testing */
export function createTestStep(
    id: number,
    options: {
        inputs?: InputTerminalSource[];
        outputs?: NewStep["outputs"];
        when?: string;
        inputConnections?: NewStep["input_connections"];
    } = {},
): NewStep {
    return {
        id,
        name: `Step ${id}`,
        type: "tool",
        inputs: options.inputs ?? [],
        outputs: options.outputs ?? [
            {
                name: "output",
                extensions: ["txt"],
                optional: false,
            },
        ],
        input_connections: options.inputConnections ?? {},
        position: { left: id * 200, top: 100 },
        post_job_actions: {},
        tool_state: {},
        workflow_outputs: [],
        when: options.when,
    };
}
