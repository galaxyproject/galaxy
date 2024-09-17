import { getFakeRegisteredUser } from "@tests/test-data";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useUserStore } from "@/stores/userStore";

import DatasetError from "./DatasetError.vue";

const localVue = getLocalVue();

const DATASET_ID = "dataset_id";

const { server, http } = useServerMock();

async function montDatasetError(has_duplicate_inputs = true, has_empty_inputs = true, user_email = "") {
    const pinia = createPinia();

    server.use(
        http.get("/api/datasets/{dataset_id}", ({ response }) => {
            // We need to use untyped here because this endpoint is not
            // described in the OpenAPI spec due to its complexity for now.
            return response.untyped(
                HttpResponse.json({
                    id: DATASET_ID,
                    creating_job: "creating_job",
                })
            );
        }),

        http.get("/api/jobs/{job_id}", ({ response }) => {
            return response(200).json({
                tool_id: "tool_id",
                tool_stderr: "tool_stderr",
                job_stderr: "job_stderr",
                job_messages: [{ desc: "message_1" }, { desc: "message_2" }],
                user_email,
                create_time: "2021-01-01T00:00:00",
                update_time: "2021-01-01T00:00:00",
                id: "job_id",
                model_class: "Job",
                state: "ok",
                inputs: {},
                outputs: {},
                params: {},
                output_collections: {},
            });
        }),

        http.get("/api/jobs/{job_id}/common_problems", ({ response }) => {
            return response(200).json({
                has_duplicate_inputs: has_duplicate_inputs,
                has_empty_inputs: has_empty_inputs,
            });
        })
    );

    const wrapper = mount(DatasetError as object, {
        propsData: {
            datasetId: DATASET_ID,
        },
        localVue,
        pinia,
    });

    const userStore = useUserStore();
    userStore.currentUser = getFakeRegisteredUser({ email: user_email });

    await flushPromises();

    return wrapper;
}

describe("DatasetError", () => {
    it("check props with common problems", async () => {
        const wrapper = await montDatasetError();

        expect(wrapper.find("#dataset-error-tool-id").text()).toBe("tool_id");
        expect(wrapper.find("#dataset-error-tool-stderr").text()).toBe("tool_stderr");
        expect(wrapper.find("#dataset-error-job-stderr").text()).toBe("job_stderr");

        const messages = wrapper.findAll("#dataset-error-job-messages .code");
        expect(messages.at(0).text()).toBe("message_1");
        expect(messages.at(1).text()).toBe("message_2");

        expect(wrapper.find("#dataset-error-has-empty-inputs")).toBeDefined();
        expect(wrapper.find("#dataset-error-has-duplicate-inputs")).toBeDefined();
    });

    it("check props without common problems", async () => {
        const wrapper = await montDatasetError(false, false, "user_email");

        expect(wrapper.find("#dataset-error-tool-id").text()).toBe("tool_id");
        expect(wrapper.find("#dataset-error-tool-stderr").text()).toBe("tool_stderr");
        expect(wrapper.find("#dataset-error-job-stderr").text()).toBe("job_stderr");

        expect(wrapper.findAll("#dataset-error-has-empty-inputs").length).toBe(0);
        expect(wrapper.findAll("#dataset-error-has-duplicate-inputs").length).toBe(0);
        expect(wrapper.findAll("#dataset-error-email").length).toBe(0);
    });

    it("hides form fields and button on success", async () => {
        const wrapper = await montDatasetError();

        server.use(
            http.post("/api/jobs/{job_id}/error", ({ response }) => {
                return response(200).json({
                    messages: [["message"], ["success"]],
                });
            })
        );

        const FormAndSubmitButton = "#dataset-error-form";
        expect(wrapper.find(FormAndSubmitButton).exists()).toBe(true);

        const submitButton = "#dataset-error-submit";
        expect(wrapper.find(submitButton).exists()).toBe(true);

        await wrapper.find(submitButton).trigger("click");

        await flushPromises();

        expect(wrapper.find(FormAndSubmitButton).exists()).toBe(false);
    });
});
