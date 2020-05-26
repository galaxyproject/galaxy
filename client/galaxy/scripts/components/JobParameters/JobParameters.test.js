import Vuex from "vuex";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { mount, createLocalVue } from "@vue/test-utils";
import flushPromises from "flush-promises";
import JobParameters from "./JobParameters";
import paramResponse from "./parameters-response.json";

const JOB_ID = "foo";

describe("JobMetrics/JobMetrics.vue", () => {
    const localVue = createLocalVue();
    localVue.use(Vuex);

    let wrapper, emitted, axiosMock;

    const linkParam = paramResponse.parameters.find((element) => Array.isArray(element.value));

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
        axiosMock.onGet(`/api/jobs/${JOB_ID}/parameters_display`).reply(200, paramResponse);
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("should not render a div if no plugins found in store", async () => {
        const propsData = {
            jobId: JOB_ID,
        };
        const wrapper = mount(JobParameters, {
            propsData,
            localVue,
        });
        await flushPromises();

        const checkTableParameter = (element, expectedTitle, expectedValue, link) => {
            const tds = element.findAll("td");
            expect(tds.length).to.equals(2);
            expect(tds.at(0).text()).to.equals(expectedTitle);
            expect(tds.at(1).text()).to.equals(expectedValue);
            if (link) {
                const a_element = tds.at(1).find("a");
                expect(a_element.attributes("href")).to.equals(link);
            }
        };
        // parameter table
        const tbody = wrapper.find("#tool-parameters > tbody");
        expect(tbody.exists()).to.equals(true);

        // table elements
        const elements = tbody.findAll("tr");
        expect(elements.length).to.equals(3);

        checkTableParameter(elements.at(0), "Add this value", "22");
        checkTableParameter(
            elements.at(1),
            linkParam.text,
            `${linkParam.value[0].hid}: ${linkParam.value[0].name}`,
            `/datasets/${linkParam.value[0].id}/show_params`
        );
        checkTableParameter(elements.at(2), "Iterate?", "NO");
    });

    it("should show only single parameter", async () => {
        const propsData = {
            jobId: JOB_ID,
            param: "Iterate?",
        };

        const getSingleParam = async (propsData) => {
            const wrapper = mount(JobParameters, {
                propsData,
                localVue,
            });
            await flushPromises();
            return wrapper.find("#single-param");
        };

        const singleParam = await getSingleParam(propsData);

        expect(singleParam.text()).to.equals("NO");

        const propsDataLink = {
            jobId: JOB_ID,
            param: linkParam.text,
        };

        const singleParamLink = await getSingleParam(propsDataLink);
        const link = singleParamLink.find("a").attributes("href");
        expect(link).to.equals(`/datasets/${linkParam.value[0].id}/show_params`);
    });
});
