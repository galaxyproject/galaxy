import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import type { JobBaseModel } from "@/api/jobs";
import { type InvocationSelection, useInvocationSelection } from "@/composables/invocationSelection";

import JobStep from "./JobStep.vue";
import JobStepJobs from "./JobStepJobs.vue";

vi.mock("@/composables/invocationSelection", () => ({ useInvocationSelection: vi.fn() }));

const { server, http } = useServerMock();
beforeEach(() => {
    server.use(http.get("/api/invocations/{invocation_id}/metrics", ({ response }) => response(200).json([])));
});

const jobs = Array.from({ length: 13 }, (_, index) => ({
    id: `job-${index}`,
    state: index === 0 ? "error" : "ok",
    update_time: `2026-01-01T00:00:${String(index).padStart(2, "0")}`,
})) as JobBaseModel[];

function setup(job: string) {
    const selection: InvocationSelection = {
        stepIndex: ref(1),
        stepTab: ref("jobs"),
        job: ref(job),
        output: ref(undefined),
    };
    vi.mocked(useInvocationSelection).mockReturnValue(selection);
    const wrapper = mount(JobStep, {
        props: { jobs, invocationId: "invocation", stepIndex: 1 },
        global: {
            plugins: [createTestingPinia({ createSpy: vi.fn })],
            stubs: { JobDetails: true, JobDetailsDisplayed: true },
        },
    });
    return { wrapper, selection };
}

describe("Invocation mapped job selection", () => {
    it("follows same-mounted selection changes to another job state and to an unknown job", async () => {
        const { wrapper, selection } = setup("job-1");
        await flushPromises();
        const table = wrapper.findComponent(JobStepJobs);
        selection.job.value = "job-0";
        await flushPromises();
        expect(table.props("jobs")).toHaveLength(1);
        expect(table.props("currentPage")).toBe(1);
        expect(wrapper.find("dialog code").text()).toContain("job-0");
        selection.job.value = "unknown-job";
        await flushPromises();
        expect(wrapper.find("dialog code").exists()).toBe(false);
        wrapper.unmount();
    });

    it("writes navigation and closing to selection while inactive cards leave the active job intact", async () => {
        const { wrapper, selection } = setup("job-2");
        await flushPromises();
        const next = wrapper.findAll("button").find((button) => button.text().trim() === "Next")!;
        await next.trigger("click");
        await flushPromises();
        expect(selection.job.value).toBe("job-1");
        selection.stepIndex.value = 2;
        selection.job.value = "other-step-job";
        await flushPromises();
        expect(selection.job.value).toBe("other-step-job");
        expect(wrapper.find("dialog code").exists()).toBe(false);
        selection.stepIndex.value = 1;
        selection.job.value = "job-1";
        await flushPromises();
        const close = wrapper.find(".g-modal-close-button");
        expect(close.exists()).toBe(true);
        await close.trigger("click");
        await flushPromises();
        expect(selection.job.value).toBeUndefined();
        wrapper.unmount();
    });
});
