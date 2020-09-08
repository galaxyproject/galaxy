import Vuex from "vuex";
import { mount, createLocalVue } from "@vue/test-utils";
import { createStore } from "../../store";
import JobDestinationParams from "./JobDestinationParams";
import jobDestinationResponse from "./testData/jobDestinationResponse";

const JOB_ID = "foo_job_id";

describe("JobDestinationParams/JobDestinationParams.vue", () => {
    const localVue = createLocalVue();
    localVue.use(Vuex);

    const responseKeys = Object.keys(jobDestinationResponse);

    let testStore;
    let wrapper;

    beforeEach(async () => {
        testStore = createStore();
        const propsData = {
            jobId: JOB_ID,
        };
        wrapper = mount(JobDestinationParams, {
            store: testStore,
            propsData,
            localVue,
            computed: {
                jobDestinationParams() {
                    return jobDestinationResponse;
                },
            },
        });
        expect(responseKeys.length > 0).toBeTruthy();
    });

    it("destination parameters should exist", async () => {
        expect(Object.keys(wrapper.vm.jobDestinationParams).length).toBe(responseKeys.length);
        expect(wrapper.vm.jobId).toBe(JOB_ID);
        expect(wrapper.vm.jobDestinationParams["docker_net"]).toBe("bridge");
        expect(wrapper.vm.jobDestinationParams["docker_set_user"]).toBeNull();
    });

    it("destination parameters should be rendered", async () => {
        const paramsTable = wrapper.find("#destination_parameters");
        expect(paramsTable.element).toBeVisible();
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
