import Vuex from "vuex";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { mount, createLocalVue } from "@vue/test-utils";
import flushPromises from "flush-promises";
import JobParameters from "./JobParameters";
import paramResponse from "./parameters-response.json";
import raw from "components/providers/test/json/Dataset.json";
import { userStore } from "store/userStore";
import { configStore } from "store/configStore";

const JOB_ID = "foo";
const DatasetProvider = {
    render() {
        return this.$scopedSlots.default({
            loading: false,
            result: raw,
        });
    },
};
const localVue = createLocalVue();

localVue.use(Vuex);

describe("JobParameters/JobParameters.vue", () => {
    let actions;
    let state;
    let store;

    const linkParam = paramResponse.parameters.find((element) => Array.isArray(element.value));
    let axiosMock;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
        axiosMock.onGet(`/api/jobs/${JOB_ID}/parameters_display`).reply(200, paramResponse);
        store = new Vuex.Store({
            modules: {
                config: {
                    state,
                    actions,
                    getters: configStore.getters,
                    namespaced: true,
                },
                user: {
                    state,
                    actions,
                    getters: userStore.getters,
                    namespaced: true,
                },
            },
        });
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("should render job parameters", async () => {
        const propsData = {
            jobId: JOB_ID,
        };

        const wrapper = mount(JobParameters, {
            propsData,
            store,
            stubs: {
                DatasetProvider: DatasetProvider,
            },
        });
        await flushPromises();

        const checkTableParameter = (element, expectedTitle, expectedValue, link) => {
            const tds = element.findAll("td");
            expect(tds.at(0).text()).toBe(expectedTitle);
            expect(tds.at(1).text()).toContain(expectedValue);
            if (link) {
                const a_element = tds.at(1).find("a");
                expect(a_element.attributes("href")).toBe(link);
            }
        };
        // parameter table
        const tbody = wrapper.find("#tool-parameters > tbody");
        expect(tbody.exists()).toBe(true);

        // table elements
        const elements = tbody.findAll("tr");
        expect(elements.length).toBe(3);

        checkTableParameter(elements.at(0), "Add this value", "22");
        checkTableParameter(elements.at(1), linkParam.text, `${raw.hid} : ${raw.name}`);
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
                stubs: {
                    DatasetProvider: DatasetProvider,
                },
            });
            await flushPromises();
            return wrapper.find("#single-param");
        };

        const singleParam = await getSingleParam(propsData);

        expect(singleParam.text()).toBe("NO");
    });
});
