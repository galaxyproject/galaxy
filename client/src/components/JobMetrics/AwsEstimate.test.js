import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it } from "vitest";

import { ensureDefined } from "@/utils/assertions";

import { ec2Instances } from "./awsEc2ReferenceData.js";

import AwsEstimate from "./AwsEstimate.vue";

const localVue = getLocalVue();

async function renderedAwsEstimate(cores, seconds, memory) {
    const jobId = Math.random().toString(36).substring(2);
    const wrapper = mount(AwsEstimate, {
        global: localVue,
        props: {
            jobId,
            jobRuntimeInSeconds: Number(seconds),
            coresAllocated: Number(cores),
            memoryAllocatedInMebibyte: Number(memory),
            ec2Instances,
        },
    });
    await flushPromises();

    if (wrapper.find("#aws-estimate").exists()) {
        return {
            cost: wrapper.get("#aws-cost").text(),
            vCpuCount: wrapper.get("#aws-vcpus").text(),
            cpu: wrapper.get("#aws-cpu").text(),
            mem: wrapper.get("#aws-mem").text(),
            name: wrapper.get("#aws-name").text(),
        };
    }
    return {};
}

function expectInstanceDetails(estimate) {
    const instance = ensureDefined(ec2Instances.find((instance) => estimate.name === instance.name));
    expect(estimate.mem).toBe(instance.mem.toString());
    expect(estimate.vCpuCount).toBe(instance.vCpuCount.toString());
    expect(estimate.cpu).toBe(instance.cpu.map(({ cpuModel }) => cpuModel).join(", "));
}

describe("JobMetrics/AwsEstimate.vue", () => {
    enableAutoUnmount(afterEach);

    it("renders nothing if no matching EC2 instance exists", async () => {
        const wrapper = mount(AwsEstimate, {
            props: {
                jobId: "0",
                jobRuntimeInSeconds: 0,
                coresAllocated: -999,
                memoryAllocatedInMebibyte: -999,
                ec2Instances,
            },
            global: localVue,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find("#aws-name").exists()).toBe(false);
    });

    it.each([
        {
            scenario: "small job",
            cores: "1.0000000",
            seconds: "9.0000000",
            memory: "2048.0000000",
            name: "t2.small",
            cost: "0.00 USD",
        },
        {
            scenario: "large job",
            cores: "40.0000000",
            seconds: "18000.0000000",
            memory: "194560.0000000",
            name: "m5d.12xlarge",
            cost: "16.32 USD",
        },
    ])("renders the instance and cost for a $scenario", async ({ cores, seconds, memory, name, cost }) => {
        const estimate = await renderedAwsEstimate(cores, seconds, memory);
        expect(estimate.name).toBe(name);
        expect(estimate.cost).toBe(cost);
        expectInstanceDetails(estimate);
    });

    it("renders no estimate when resource requirements exceed available instances", async () => {
        const estimate = await renderedAwsEstimate("99999.0000000", "18000.0000000", "99999.0000000");
        expect(estimate).toEqual({});
    });
});
