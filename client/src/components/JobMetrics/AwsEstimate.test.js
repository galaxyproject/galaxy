import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { ec2Instances } from "./awsEc2ReferenceData.js";
import AwsEstimate from "./AwsEstimate";

const localVue = getLocalVue();

describe("JobMetrics/AwsEstimate.vue", () => {
    it("renders nothing if no matching EC2 instance exists.", async () => {
        const wrapper = mount(AwsEstimate, {
            propsData: {
                jobId: "0",
                jobRuntimeInSeconds: 0,
                coresAllocated: -999,
                memoryAllocatedInMebibyte: -999,
                ec2Instances,
            },
            localVue,
        });

        await wrapper.vm.$nextTick();
        expect(wrapper.find("#aws-name").exists()).toBe(false);
    });

    it("renders correct AWS estimates.", async () => {
        const deriveRenderedAwsEstimate = async (cores, seconds, memory) => {
            const JOB_ID = Math.random().toString(36).substring(2);

            const wrapper = mount(AwsEstimate, {
                localVue,
                propsData: {
                    jobId: JOB_ID,
                    jobRuntimeInSeconds: Number(seconds),
                    coresAllocated: Number(cores),
                    memoryAllocatedInMebibyte: Number(memory),
                    ec2Instances,
                },
            });

            await flushPromises();

            if (wrapper.find("#aws-estimate").exists()) {
                return {
                    cost: wrapper.find("#aws-cost").text(),
                    vCpuCount: wrapper.find("#aws-vcpus").text(),
                    cpu: wrapper.find("#aws-cpu").text(),
                    mem: wrapper.find("#aws-mem").text(),
                    name: wrapper.find("#aws-name").text(),
                };
            }

            return {};
        };

        const assertAwsInstance = (estimates) => {
            const instance = ec2Instances.find((instance) => estimates.name === instance.name);
            expect(estimates.mem).toBe(instance.mem.toString());
            expect(estimates.vCpuCount).toBe(instance.vCpuCount.toString());
            expect(estimates.cpu).toBe(instance.cpu.map(({ cpuModel }) => cpuModel).join(", "));
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
        expect(estimates_not_available).toEqual({});
    });
});
