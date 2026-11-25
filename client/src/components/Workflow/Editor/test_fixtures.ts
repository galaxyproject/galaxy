import type { UseElementBoundingReturn } from "@vueuse/core";
import { reactive, toRefs } from "vue";

import type { InputTerminalSource, NewStep, Step, Steps } from "@/stores/workflowStepStore";

import _advancedSteps from "./test-data/parameter_steps.json";
import _simpleSteps from "./test-data/simple_steps.json";

const _mockOffset = toRefs(reactive({ top: 0, left: 0, bottom: 10, right: 10, width: 100, height: 100, x: 0, y: 0 }));
// eslint-disable-next-line @typescript-eslint/no-empty-function
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
        type?: NewStep["type"];
        label?: string;
        configForm?: NewStep["config_form"];
        postJobActions?: NewStep["post_job_actions"];
    } = {},
): Step {
    return {
        id,
        name: `Step ${id}`,
        type: options.type ?? "tool",
        label: options.label,
        config_form: options.configForm,
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
        post_job_actions: options.postJobActions ?? {},
        tool_state: {},
        workflow_outputs: [],
        when: options.when,
    };
}
