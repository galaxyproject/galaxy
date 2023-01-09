import { toRefs, reactive } from "vue";
import type { UseElementBoundingReturn } from "@vueuse/core";
import type { Steps } from "@/stores/workflowStepStore";
import * as _simpleSteps from "./test-data/simple_steps.json";
import * as _advancedSteps from "./test-data/parameter_steps.json";

const _mockOffset = toRefs(reactive({ top: 0, left: 0, bottom: 10, right: 10, width: 100, height: 100, x: 0, y: 0 }));
// eslint-disable-next-line @typescript-eslint/no-empty-function
export const mockOffset: UseElementBoundingReturn = { ..._mockOffset, update: () => {} };

export const simpleSteps = _simpleSteps as Steps;
export const advancedSteps = _advancedSteps as Steps;
