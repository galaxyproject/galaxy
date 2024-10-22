import { getFakeRegisteredUser } from "@tests/test-data";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";
import { useUserStore } from "@/stores/userStore";

import jobDestinationResponseData from "./testData/jobDestinationResponse.json";

import JobDestinationParams from "./JobDestinationParams.vue";

const JOB_ID = "foo_job_id";

const localVue = getLocalVue();

const jobDestinationResponse = jobDestinationResponseData as Record<string, string | null>;

const { server, http } = useServerMock();

async function mountJobDestinationParams() {
    server.use(
        http.get("/api/jobs/{job_id}/destination_params", ({ response }) => {
            return response(200).json(jobDestinationResponse);
        })
    );

    const pinia = createPinia();
    const wrapper = shallowMount(JobDestinationParams as object, {
        propsData: {
            jobId: JOB_ID,
        },
        localVue,
        pinia,
    });

    const userStore = useUserStore();
    userStore.currentUser = getFakeRegisteredUser({ is_admin: true });

    await flushPromises();

    return wrapper;
}

describe("JobDestinationParams/JobDestinationParams.vue", () => {
    const responseKeys = Object.keys(jobDestinationResponse);
    expect(responseKeys.length > 0).toBeTruthy();

    it("should render destination parameters", async () => {
        const wrapper = await mountJobDestinationParams();

        const paramsTable = wrapper.find("#destination_parameters");
        expect(paramsTable.exists()).toBe(true);
        const params = paramsTable.findAll("tbody > tr");
        expect(params.length).toBe(responseKeys.length);

        for (let counter = 0; counter < responseKeys.length - 1; counter++) {
            const parameter = params.at(counter).findAll("td");
            const parameterTitle = parameter.at(0).text();
            const parameterValue = parameter.at(1).text();

            expect(responseKeys.includes(parameterTitle)).toBeTruthy();
            // since we render null as an empty string, rendered empty string should always equal null in test data
            expect(
                jobDestinationResponse[parameterTitle] === (parameterValue === "" ? null : parameterValue)
            ).toBeTruthy();
        }
    });
});
