import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import Lint from "./Lint";

jest.mock("./modules/utilities");
jest.mock("app");

import { getDisconnectedInputs, getInputsMissingMetadata, getWorkflowOutputs } from "./modules/linting";

const localVue = getLocalVue();

describe("Lint", () => {
    let wrapper;

    beforeEach(() => {
        getDisconnectedInputs.mockReturnValue([{}]);
        getWorkflowOutputs.mockReturnValue([{}]);
        getInputsMissingMetadata.mockReturnValue([{}]);
        wrapper = shallowMount(Lint, {
            localVue,
        });
    });

    function getExpectedRefactoring() {
        expect(wrapper.emitted().refactor.length).toBe(1);
        return wrapper.emitted().refactor[0][0];
    }

    function getExpectedAction() {
        const refactor = getExpectedRefactoring();
        expect(refactor.length).toBe(1);
        return refactor[0];
    }

    it("should fire a refactor event on extracting a disconnected input", async () => {
        wrapper.vm.extractWorkflowInput({
            stepId: "45",
            inputName: "my_input",
        });
        await wrapper.vm.$nextTick();
        const action = getExpectedAction();
        expect(action.action_type).toBe("extract_input");
        expect(action.input.order_index).toBe(45);
        expect(action.input.input_name).toBe("my_input");
    });

    it("should fire a refactor on extracting legacy parameter", async () => {
        wrapper.vm.extractLegacyParameter({
            name: "run_id",
        });
        await wrapper.vm.$nextTick();
        const action = getExpectedAction();
        expect(action.action_type).toBe("extract_legacy_parameter");
        expect(action.name).toBe("run_id");
    });

    it("should fire a refactor on removing unlabeled outputs", async () => {
        wrapper.vm.removeUnlabeledWorkflowOutputs();
        await wrapper.vm.$nextTick();
        const action = getExpectedAction();
        expect(action.action_type).toBe("remove_unlabeled_workflow_outputs");
    });
});
