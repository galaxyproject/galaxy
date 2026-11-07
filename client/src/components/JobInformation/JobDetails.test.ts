import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { JobBaseModel } from "@/api/jobs";

import JobDetails from "./JobDetails.vue";

const localVue = getLocalVue();
const { server, http } = useServerMock();

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

    it("mounts no fetching children when the job fails to load", async () => {
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) =>
                response.untyped(HttpResponse.json({ err_msg: "Invalid id" }, { status: 400 })),
            ),
        );
        const wrapper = mount(JobDetails as object, {
            props: { jobId: "bad-id" },
            global: {
                ...localVue,
                plugins: [createTestingPinia({ createSpy: vi.fn, stubActions: false })],
                stubs: { JobInformation: true, JobParameters: true, JobMetrics: true },
            },
        });
        await flushPromises();

        expect(wrapper.text()).toContain("Invalid id");
        ["JobInformation", "JobParameters", "JobMetrics"].forEach((name) =>
            expect(wrapper.findComponent({ name }).exists()).toBe(false),
        );
    });
});
