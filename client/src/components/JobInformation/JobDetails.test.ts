import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { JobBaseModel } from "@/api/jobs";

import JobDetails from "./JobDetails.vue";

const localVue = getLocalVue();

const JobInformationStub = {
    name: "JobInformation",
    template: "<div><slot name='extra-code-rows' /></div>",
};

describe("JobDetails", () => {
    it("shows the traceback of a job passed in from the admin job list", () => {
        const adminListJob = { id: "job1", state: "error", traceback: "Traceback (most recent call last): ..." };
        const wrapper = mount(JobDetails as object, {
            props: { job: adminListJob as unknown as JobBaseModel },
            global: {
                ...localVue,
                stubs: { JobInformation: JobInformationStub, JobParameters: true, JobMetrics: true, HelpText: true },
            },
        });

        expect(wrapper.text()).toContain("Traceback (most recent call last): ...");
    });
});
