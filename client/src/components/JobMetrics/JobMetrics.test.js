import { mount, createLocalVue } from "@vue/test-utils";
import flushPromises from "flush-promises";
import JobMetrics from "./JobMetrics";
import ec2 from "./ec2.json";
import Vuex from "vuex";
import createCache from "vuex-cache";
import { jobMetricsStore } from "store/jobMetricsStore";

const JOB_ID = "moo";

// Ignore all axios calls, data is mocked locally -- just say "OKAY!"
jest.mock("axios", () => ({
    get: async () => {
        return { response: { status: 200 } };
    },
}));

const localVue = createLocalVue();
localVue.use(Vuex);
const testStore = new Vuex.Store({
    plugins: [createCache()],
    modules: {
        jobMetricsStore,
    },
});

describe("JobMetrics/JobMetrics.vue", () => {
    it("should not render a div if no plugins found in store", async () => {
        const propsData = {
            jobId: JOB_ID,
        };
        const wrapper = mount(JobMetrics, {
            store: testStore,
            propsData,
            localVue,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find("div").exists()).toBe(false);
    });

    it("should group plugins by type", async () => {
        const propsData = {
            jobId: JOB_ID,
        };
        const metricsResponse = [
            { plugin: "core", title: "runtime", value: 145 },
            { plugin: "core", title: "memory", value: 146 },
            { plugin: "extended", title: "awesomeness", value: 42 },
        ];
        const wrapper = mount(JobMetrics, {
            store: testStore,
            propsData,
            localVue,
            computed: {
                jobMetrics() {
                    return metricsResponse;
                },
            },
        });
        // Wait for axios and rendering.
        await flushPromises();
        expect(wrapper.vm.jobMetrics.length).toBe(3);
        expect(wrapper.vm.jobId).toBe(JOB_ID);
        expect(wrapper.vm.metricsByPlugins.core.runtime).toBe(145);
        expect(wrapper.vm.orderedPlugins.length).toBe(2);
        // Three metrics, begin metrics for two plugins
        const metricsTables = wrapper.findAll(".metrics_plugin");
        expect(metricsTables.length).toBe(2);
        expect(metricsTables.at(0).find(".metrics_plugin_title").text()).toBe("core");
        expect(metricsTables.at(0).findAll("tr").length).toBe(2);
        expect(metricsTables.at(1).find(".metrics_plugin_title").text()).toBe("extended");
        expect(metricsTables.at(1).findAll("tr").length).toBe(1);
    });

    it("should render correct AWS Estimates", async () => {
        const deriveRenderedAwsEstimate = async (cores, seconds, memory) => {
            const JOB_ID = Math.random().toString(36).substring(2);
            const propsData = {
                jobId: JOB_ID,
                aws_estimate: true,
            };
            const metricsResponse = [
                { plugin: "core", name: "galaxy_slots", raw_value: cores },
                { plugin: "core", name: "runtime_seconds", raw_value: seconds },
                { plugin: "core", name: "galaxy_memory_mb", raw_value: memory },
            ];
            const wrapper = mount(JobMetrics, {
                store: testStore,
                propsData,
                localVue,
                computed: {
                    jobMetrics() {
                        return metricsResponse;
                    },
                },
            });
            // Wait for axios and rendering.
            await flushPromises();

            const estimates = {};

            if (!wrapper.find("#aws-estimate").exists()) {
                return false;
            }

            estimates.cost = wrapper.find("#aws-estimate b").text();
            estimates.vcpus = wrapper.find("#aws_vcpus").text();
            estimates.cpu = wrapper.find("#aws_cpu").text();
            estimates.mem = wrapper.find("#aws_mem").text();
            estimates.name = wrapper.find("#aws_name").text();

            return estimates;
        };
        const assertAwsInstance = (estimates) => {
            const instance = ec2.find((instance) => estimates.name === instance.name);
            expect(estimates.mem).toBe(instance.mem.toString());
            expect(estimates.vcpus).toBe(instance.vcpus.toString());
            expect(estimates.cpu).toBe(instance.cpu.toString());
        };

        const estimates_small = await deriveRenderedAwsEstimate("1.0000000", "9.0000000", "2048.0000000");

        expect(estimates_small.name).toBe("t2.small");
        expect(estimates_small.cost).toBe("0.00 USD");
        assertAwsInstance(estimates_small);

        const estimates_large = await deriveRenderedAwsEstimate("40.0000000", "18000.0000000", "194560.0000000");
        expect(estimates_large.name).toBe("m5d.12xlarge");
        expect(estimates_large.cost).toBe("16.32 USD");
        assertAwsInstance(estimates_large);

        const estimates_not_available = await deriveRenderedAwsEstimate(
            "99999.0000000",
            "18000.0000000",
            "99999.0000000"
        );
        expect(estimates_not_available).toBe(false);
    });
});
