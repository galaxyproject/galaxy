import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import JobMetrics from "./JobMetrics";

const NO_METRICS_MESSAGE = "No metrics available for this job.";

// Ignore all axios calls, data is mocked locally -- just say "OKAY!"
jest.mock("axios", () => ({
    get: async () => {
        return { response: { status: 200 } };
    },
}));

const localVue = getLocalVue();

describe("JobMetrics/JobMetrics.vue", () => {
    it("should not render a div if no plugins found in store", async () => {
        const wrapper = mount(JobMetrics, {
            pinia: createTestingPinia(),
            propsData: {
                jobId: "9000",
            },
            localVue,
        });

        await wrapper.vm.$nextTick();
        const alert = wrapper.find(".alert-info");
        expect(alert.text()).toBe(NO_METRICS_MESSAGE);
    });

    it("should group plugins by type", async () => {
        const JOB_ID = "9000";
        const mockMetricsResponse = [
            { plugin: "core", title: "runtime", value: 145 },
            { plugin: "core", title: "memory", value: 146 },
            { plugin: "extended", title: "awesomeness", value: 42 },
        ];

        const pinia = createTestingPinia({
            initialState: {
                jobMetricsStore: {
                    jobMetricsByJobId: {
                        [`${JOB_ID}`]: mockMetricsResponse,
                    },
                    jobMetricsByHdaId: {},
                    jobMetricsByLddaId: {},
                },
            },
        });
        setActivePinia(pinia);

        const wrapper = mount(JobMetrics, {
            localVue,
            pinia,
            propsData: {
                jobId: JOB_ID,
            },
        });

        // Wait for axios and rendering.
        await flushPromises();

        // Three metrics, begin metrics for two plugins
        const metricsTables = wrapper.findAll(".metrics_plugin");
        expect(metricsTables.length).toBe(2);
        expect(metricsTables.at(0).find(".metrics_plugin_title").text()).toBe("core");
        expect(metricsTables.at(0).findAll("tr").length).toBe(2);
        expect(metricsTables.at(1).find(".metrics_plugin_title").text()).toBe("extended");
        expect(metricsTables.at(1).findAll("tr").length).toBe(1);
    });
});
