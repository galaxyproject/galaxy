import Vuex from "vuex";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { mount, createLocalVue } from "@vue/test-utils";
import { createStore } from "../../store";
import flushPromises from "flush-promises";
import JobMetrics from "./JobMetrics";
import ec2 from "./ec2.json";

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
            jobId: JOB_ID,
        };
        const wrapper = mount(JobMetrics, {
            store: testStore,
            propsData,
            localVue,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.isEmpty()).to.equals(true);
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
        axiosMock.onGet(`/api/jobs/${JOB_ID}/metrics`).reply(200, metricsResponse);
        const wrapper = mount(JobMetrics, {
            store: testStore,
            propsData,
            localVue,
        });
        // Wait for axios and rendering.
        await flushPromises();
        expect(wrapper.vm.jobMetrics.length).to.equals(3);
        expect(wrapper.vm.jobId).to.equals(JOB_ID);
        expect(wrapper.vm.metricsByPlugins.core.runtime).to.equals(145);
        expect(wrapper.vm.orderedPlugins.length).to.equals(2);
        // Three metrics, begin metrics for two plugins
        const metricsTables = wrapper.findAll(".metrics_plugin");
        expect(metricsTables.length).to.equals(2);
        expect(metricsTables.at(0).find(".metrics_plugin_title").text()).to.equals("core");
        expect(metricsTables.at(0).findAll("tr").length).to.equals(2);
        expect(metricsTables.at(1).find(".metrics_plugin_title").text()).to.equals("extended");
        expect(metricsTables.at(1).findAll("tr").length).to.equals(1);
    });

    it("should render correct AWS Estimates", async () => {
        let deriveRenderedAwsEstimate = async (cores, seconds, memory) => {
            const JOB_ID = Math.random().toString(36).substring(2);
            const propsData = {
                jobId: JOB_ID,
                aws_estimate: "True",
            };
            const metricsResponse = [
                { plugin: "core", name: "galaxy_slots", raw_value: cores },
                { plugin: "core", name: "runtime_seconds", raw_value: seconds },
                { plugin: "core", name: "galaxy_memory_mb", raw_value: memory },
            ];
            axiosMock.onGet(`/api/jobs/${JOB_ID}/metrics`).reply(200, metricsResponse);
            const wrapper = mount(JobMetrics, {
                store: testStore,
                propsData,
                localVue,
            });
            // Wait for axios and rendering.
            await flushPromises();

            const estimates = {};

            if (!wrapper.find("#aws-estimate").exists()) return false;

            estimates.cost = wrapper.find("#aws-estimate > b").text();
            estimates.vcpus = wrapper.find("#aws_vcpus").text();
            estimates.cpu = wrapper.find("#aws_cpu").text();
            estimates.mem = wrapper.find("#aws_mem").text();
            estimates.name = wrapper.find("#aws_name").text();

            return estimates;
        };
        let assertAwsInstance = (estimates) => {
            const instance = ec2.find((instance) => estimates.name === instance.name);
            expect(estimates.mem).to.equals(instance.mem.toString());
            expect(estimates.vcpus).to.equals(instance.vcpus.toString());
            expect(estimates.cpu).to.equals(instance.cpu.toString());
        };

        let estimates_small = await deriveRenderedAwsEstimate("1.0000000", "9.0000000", "2048.0000000");

        expect(estimates_small.name).to.equals("t2.small");
        expect(estimates_small.cost).to.equals("0.00 USD");
        assertAwsInstance(estimates_small);

        let estimates_large = await deriveRenderedAwsEstimate("40.0000000", "18000.0000000", "194560.0000000");
        expect(estimates_large.name).to.equals("m5d.12xlarge");
        expect(estimates_large.cost).to.equals("16.32 USD");
        assertAwsInstance(estimates_large);

        let estimates_not_available = await deriveRenderedAwsEstimate(
            "99999.0000000",
            "18000.0000000",
            "99999.0000000"
        );
        expect(estimates_not_available).to.equals(false);
    });
});
