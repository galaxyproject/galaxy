import Vuex from "vuex";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { mount, createLocalVue } from "@vue/test-utils";
import { createStore } from "../../store";
import JobMetrics from "./JobMetrics";

const JOB_ID = "moo";

describe("JobMetrics/JobMetrics.vue", () => {
    const localVue = createLocalVue();
    localVue.use(Vuex);

    let testStore, axiosMock;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
        testStore = createStore();
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("should not render a div if no plugins found in store", async () => {
        const propsData = {
            jobId: JOB_ID
        };
        const wrapper = mount(JobMetrics, {
            store: testStore,
            propsData,
            localVue
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.isEmpty()).to.equals(true);
    });

    it("should group plugins by type", async () => {
        const propsData = {
            jobId: JOB_ID
        };
        const metricsResponse = [
            { plugin: "core", title: "runtime", value: 145 },
            { plugin: "core", title: "memory", value: 146 },
            { plugin: "extended", title: "awesomeness", value: 42 }
        ];
        axiosMock.onGet(`/api/jobs/${JOB_ID}/metrics`).reply(200, metricsResponse);
        const wrapper = mount(JobMetrics, {
            store: testStore,
            propsData,
            localVue
        });
        // One tick for axios request.
        await wrapper.vm.$nextTick();
        // One tick for Vue to render.
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.jobMetrics.length).to.equals(3);
        expect(wrapper.vm.jobId).to.equals(JOB_ID);
        expect(wrapper.vm.metricsByPlugins.core.runtime).to.equals(145);
        expect(wrapper.vm.orderedPlugins.length).to.equals(2);
        // Three metrics, begin metrics for two plugins
        const metricsTables = wrapper.findAll(".metrics_plugin");
        expect(metricsTables.length).to.equals(2);
        expect(
            metricsTables
                .at(0)
                .find(".metrics_plugin_title")
                .text()
        ).to.equals("core");
        expect(metricsTables.at(0).findAll("tr").length).to.equals(2);
        expect(
            metricsTables
                .at(1)
                .find(".metrics_plugin_title")
                .text()
        ).to.equals("extended");
        expect(metricsTables.at(1).findAll("tr").length).to.equals(1);
    });
});
