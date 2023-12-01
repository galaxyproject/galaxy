import { shallowMount, Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { mockFetcher } from "@/api/schema/__mocks__";
import { useUserStore } from "@/stores/userStore";

import jobDestinationResponseData from "./testData/jobDestinationResponse.json";

import JobDestinationParams from "./JobDestinationParams.vue";

const JOB_ID = "foo_job_id";

jest.mock("@/api/schema");

const localVue = getLocalVue();

const jobDestinationResponse = jobDestinationResponseData as Record<string, string | null>;

describe("JobDestinationParams/JobDestinationParams.vue", () => {
    const responseKeys = Object.keys(jobDestinationResponse);
    expect(responseKeys.length > 0).toBeTruthy();

    let wrapper: Wrapper<Vue>;

    beforeEach(async () => {
        const propsData = {
            jobId: JOB_ID,
        };

        mockFetcher.path("/api/jobs/{job_id}/destination_params").method("get").mock({ data: jobDestinationResponse });

        const pinia = createPinia();
        wrapper = shallowMount(JobDestinationParams as object, {
            propsData,
            localVue,
            pinia,
        });

        const userStore = useUserStore();
        userStore.currentUser = {
            email: "admin@email",
            id: "1",
            tags_used: [],
            isAnonymous: false,
            total_disk_usage: 1048576,
            is_admin: true,
        };

        await flushPromises();
    });

    it("destination parameters should exist", async () => {
        expect(Object.keys(wrapper.vm.jobDestinationParams).length).toBe(responseKeys.length);
        expect(wrapper.vm.jobId).toBe(JOB_ID);
        expect(wrapper.vm.jobDestinationParams["docker_net"]).toBe("bridge");
        expect(wrapper.vm.jobDestinationParams["docker_set_user"]).toBeNull();
    });

    it("should render destination parameters", async () => {
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
