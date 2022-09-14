import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import DatasetError from "./DatasetError";
import MockProvider from "../providers/MockProvider";

jest.mock("components/providers", () => {
    return {}; // stubbed below
});

const localVue = getLocalVue();

function buildWrapper(has_duplicate_inputs = true, has_empty_inputs = true, user_email = "") {
    return mount(DatasetError, {
        propsData: {
            datasetId: "dataset_id",
        },
        localVue,
        stubs: {
            JobDetailsProvider: MockProvider({
                result: {
                    tool_id: "tool_id",
                    tool_stderr: "tool_stderr",
                    job_stderr: "job_stderr",
                    job_messages: [{ desc: "message_1" }, { desc: "message_2" }],
                    user_email: user_email,
                },
            }),
            JobProblemProvider: MockProvider({
                result: { has_duplicate_inputs: has_duplicate_inputs, has_empty_inputs: has_empty_inputs },
            }),
            DatasetProvider: MockProvider({
                result: { id: "dataset_id", creating_job: "creating_job" },
            }),
            FontAwesomeIcon: false,
            FormElement: false,
        },
    });
}

describe("DatasetError", () => {
    it("check props with common problems", async () => {
        const wrapper = buildWrapper();
        expect(wrapper.find("#dataset-error-tool-id").text()).toBe("tool_id");
        expect(wrapper.find("#dataset-error-tool-stderr").text()).toBe("tool_stderr");
        expect(wrapper.find("#dataset-error-job-stderr").text()).toBe("job_stderr");
        const messages = wrapper.findAll("#dataset-error-job-messages .code");
        expect(messages.at(0).text()).toBe("message_1");
        expect(messages.at(1).text()).toBe("message_2");
        expect(wrapper.find("#dataset-error-has-empty-inputs")).toBeDefined();
        expect(wrapper.find("#dataset-error-has-duplicate-inputs")).toBeDefined();
        expect(wrapper.findAll("#dataset-error-email").length).toBe(1);
    });

    it("check props without common problems", async () => {
        const wrapper = buildWrapper(false, false, "user_email");
        expect(wrapper.find("#dataset-error-tool-id").text()).toBe("tool_id");
        expect(wrapper.find("#dataset-error-tool-stderr").text()).toBe("tool_stderr");
        expect(wrapper.find("#dataset-error-job-stderr").text()).toBe("job_stderr");
        expect(wrapper.findAll("#dataset-error-has-empty-inputs").length).toBe(0);
        expect(wrapper.findAll("#dataset-error-has-duplicate-inputs").length).toBe(0);
        expect(wrapper.findAll("#dataset-error-email").length).toBe(0);
    });

    it("hides form fields and button on success", async () => {
        const wrapper = buildWrapper();
        const fieldsAndButton = "#fieldsAndButton";
        expect(wrapper.find(fieldsAndButton).exists()).toBe(true);
        await wrapper.setData({ resultMessages: [["message", "success"]] });
        expect(wrapper.find(fieldsAndButton).exists()).toBe(false);
    });

    it("does not hide form fields and button on error", async () => {
        const wrapper = buildWrapper();
        const fieldsAndButton = "#fieldsAndButton";
        expect(wrapper.find(fieldsAndButton).exists()).toBe(true);
        const messages = [
            ["message", "success"],
            ["message", "danger"],
        ]; // at least one has "danger"
        await wrapper.setData({ resultMessages: messages });
        expect(wrapper.find(fieldsAndButton).exists()).toBe(true);
    });
});
