import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import DatasetError from "./DatasetError";
import MockProvider from "../providers/MockProvider";

jest.mock("components/WorkflowInvocationState/providers", () => {
    return {}; // stubbed below
});

const localVue = getLocalVue();

describe("DatasetError", () => {
    let wrapper;
    
    beforeEach(() => {
        wrapper = mount(DatasetError, {
            propsData: {
                datasetId: "dataset_id",
            },
            localVue,
            stubs: {
                JobDetailsProvider: MockProvider({
                    result: { tool_id: "tool_id", tool_stderr: "tool_stderr", job_stderr: "job_stderr" },
                }),
                JobProblemProvider: MockProvider({ result: { has_duplicate_inputs: true, has_empty_inputs: true } }),
                DatasetProvider: MockProvider({
                    resultLabel: "item",
                    result: { id: "dataset_id", creating_job: "creating_job" },
                }),
                FontAwesomeIcon: false,
                FormElement: false,
            },
        });
    });

    it("check props", async () => {
        expect(wrapper.find("#dataset-error-tool-id").text()).toBe("tool_id");
        expect(wrapper.find("#dataset-error-tool-stderr").text()).toBe("tool_stderr");
    });
});
