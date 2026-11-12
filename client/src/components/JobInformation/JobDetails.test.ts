import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { JobBaseModel } from "@/api/jobs";
import { useUserStore } from "@/stores/userStore";

import JobDetails from "./JobDetails.vue";

const localVue = getLocalVue();

const JobInformationStub = {
    name: "JobInformation",
    template: "<div><slot name='extra-code-rows' /></div>",
};

function mountJobDetails(isAdmin: boolean) {
    const localVue = getLocalVue();
    useUserStore().currentUser = getFakeRegisteredUser({ is_admin: isAdmin });
    return mount(JobDetails as object, {
        props: { jobId: "job1" },
        global: {
            ...localVue,
            stubs: { JobInformation: true, JobParameters: true, JobMetrics: true, JobDestinationParams: true },
        },
    });
}

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

    it("shows destination parameters to admins", () => {
        const wrapper = mountJobDetails(true);
        expect(wrapper.findComponent({ name: "JobDestinationParams" }).exists()).toBe(true);
    });

    it("hides destination parameters from non-admins", () => {
        const wrapper = mountJobDetails(false);
        expect(wrapper.findComponent({ name: "JobDestinationParams" }).exists()).toBe(false);
    });
});
