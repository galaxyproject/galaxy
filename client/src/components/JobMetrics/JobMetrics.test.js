import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, vi } from "vitest";

import JobMetrics from "./JobMetrics.vue";

const JOB_ID = "9000";
const NO_METRICS_MESSAGE = "No metrics available for this job.";

const SELECTORS = {
    NO_METRICS_ALERT: ".alert-info",
    PLUGIN: ".metrics_plugin",
    PLUGIN_TITLE: ".metrics_plugin_title",
};

const localVue = getLocalVue();

enableAutoUnmount(afterEach);

/** The testing store stubs the metrics fetch, so tests seed what it would have loaded. */
async function mountJobMetrics(jobMetricsByJobId = {}) {
    const pinia = createTestingPinia({
        createSpy: vi.fn,
        initialState: { jobMetricsStore: { jobMetricsByJobId } },
    });
    const wrapper = mount(JobMetrics, {
        props: { jobId: JOB_ID },
        global: withPlugins(localVue, pinia),
    });
    await flushPromises();
    return wrapper;
}

describe("JobMetrics", () => {
    it("shows the no-metrics message when the store has no metrics for the job", async () => {
        const wrapper = await mountJobMetrics();

        expect(wrapper.find(SELECTORS.NO_METRICS_ALERT).text()).toBe(NO_METRICS_MESSAGE);
        expect(wrapper.find(SELECTORS.PLUGIN).exists()).toBe(false);
    });

    it("groups metrics into one table per plugin", async () => {
        const wrapper = await mountJobMetrics({
            [JOB_ID]: [
                { plugin: "core", title: "runtime", value: 145 },
                { plugin: "core", title: "memory", value: 146 },
                { plugin: "extended", title: "awesomeness", value: 42 },
            ],
        });

        const plugins = wrapper.findAll(SELECTORS.PLUGIN).map((plugin) => ({
            title: plugin.find(SELECTORS.PLUGIN_TITLE).text(),
            rows: plugin.findAll("tr").length,
        }));
        expect(plugins).toEqual([
            { title: "core", rows: 2 },
            { title: "extended", rows: 1 },
        ]);
        expect(wrapper.find(SELECTORS.NO_METRICS_ALERT).exists()).toBe(false);
    });
});
