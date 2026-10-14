import { composeStories } from "@storybook/vue3-vite";
import { getLocalVue } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it } from "vitest";

import { ec2Instances } from "./awsEc2ReferenceData.js";
import * as AwsEstimateStories from "./AwsEstimate.stories";

import AwsEstimate from "./AwsEstimate.vue";

const stories = composeStories(AwsEstimateStories);
const mountStory = useStoryMount();
const localVue = getLocalVue();

async function renderedAwsEstimate(cores, seconds, memory, story = stories.ShortSingleCoreJob) {
    const wrapper = mountStory(story, {
        props: {
            jobRuntimeInSeconds: Number(seconds),
            coresAllocated: Number(cores),
            memoryAllocatedInMebibyte: Number(memory),
        },
    });
    await flushPromises();

    let estimate = {};
    if (wrapper.find("#aws-estimate").exists()) {
        estimate = {
            cost: wrapper.get("#aws-cost").text(),
            vCpuCount: wrapper.get("#aws-vcpus").text(),
            cpu: wrapper.get("#aws-cpu").text(),
            mem: wrapper.get("#aws-mem").text(),
            name: wrapper.get("#aws-name").text(),
        };
    }
    return { estimate, wrapper };
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
        expect(wrapper.find("#aws-estimate").exists()).toBe(false);
        expect(wrapper.text()).toBe("");
    });

    it("renders no estimate when resource requirements exceed available instances", async () => {
        const { estimate, wrapper } = await renderedAwsEstimate("99999.0000000", "18000.0000000", "99999.0000000");
        expect(estimate).toEqual({});
        expect(wrapper.find("#aws-estimate").exists()).toBe(false);
        expect(wrapper.text()).toBe("");
    });
});
