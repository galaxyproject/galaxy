import Vuex from "vuex";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { mount, createLocalVue } from "@vue/test-utils";
import { createStore } from "../../store";
import flushPromises from "flush-promises";
import JobDestinationParams from "./JobDestinationParams";
import jobDestinationResponse from "./testData/jobDestinationResponse";

const JOB_ID = "foo_job_id";

describe("JobDestinationParams/JobDestinationParams.vue", () => {
    const localVue = createLocalVue();
    localVue.use(Vuex);

    const responseKeys = Object.keys(jobDestinationResponse);

    let testStore, axiosMock, wrapper;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        testStore = createStore();
        const propsData = {
            jobId: JOB_ID,
        };
        axiosMock.onGet(`/api/jobs/${JOB_ID}/destination_params`).reply(200, jobDestinationResponse);
        wrapper = mount(JobDestinationParams, {
            store: testStore,
            propsData,
            localVue,
        });
        await flushPromises();
        assert(responseKeys.length > 0, "test data is invalid!");
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("destination parameters should exist", async () => {
        expect(Object.keys(wrapper.vm.jobDestinationParams).length).to.equals(responseKeys.length);
        expect(wrapper.vm.jobId).to.equals(JOB_ID);
        expect(wrapper.vm.jobDestinationParams["docker_net"]).to.equals("bridge");
        expect(wrapper.vm.jobDestinationParams["docker_set_user"]).to.equals(null);
    });

    it("destination parameters should be rendered", async () => {
        console.log(wrapper.html());
        const paramsTable = wrapper.find("#destination_parameters");
        expect(paramsTable.isVisible()).to.equals(true);
        const params = paramsTable.findAll("tbody > tr");
        expect(params.length).to.equals(responseKeys.length);

        for (let counter = 0; counter < responseKeys.length - 1; counter++) {
            const parameter = params.at(counter).findAll("td");
            const parameterTitle = parameter.at(0).text();
            const parameterValue = parameter.at(1).text();

            assert(responseKeys.includes(parameterTitle), "rendered parameter should exist in test data!");
            // since we render null as an empty string, rendered empty string should always equal null in test data
            assert(
                jobDestinationResponse[parameterTitle] === (parameterValue === "" ? null : parameterValue),
                "parameter value is not equal to test data!"
            );
        }
    });
});
