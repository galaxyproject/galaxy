import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { RegisteredUser } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import type { JobBaseModel, JobState as JobStateType, ShowFullJobResponse } from "@/api/jobs";
import { useUserStore } from "@/stores/userStore";

import JobState from "./JobState.vue";

vi.mock("vue-router/composables", () => ({
    useRoute: vi.fn(() => ({})),
}));

const localVue = getLocalVue();
const { server, http } = useServerMock();

const FAKE_USER = getFakeRegisteredUser({ id: "user-123" });

const BASE_JOB: JobBaseModel = {
    model_class: "Job",
    id: "job-abc",
    state: "running",
    tool_id: "some_tool",
    create_time: "2024-01-01T00:00:00",
    update_time: "2024-01-01T00:01:00",
};

const FULL_JOB = {
    ...BASE_JOB,
    inputs: {},
    outputs: {},
    output_collections: {},
    params: {},
    user_id: "user-123",
} as ShowFullJobResponse;

const SELECTORS = {
    STOP_BTN: ".stop-job-btn",
    STATE_BADGE: ".job-state-badge",
};

function mountJobState(job: JobBaseModel | ShowFullJobResponse, user: RegisteredUser | null = FAKE_USER) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    const userStore = useUserStore();
    userStore.currentUser = user;
    return mount(JobState as object, {
        propsData: { job },
        localVue,
        pinia,
    });
}

describe("JobState.vue", () => {
    beforeEach(() => {
        server.use(
            http.delete("/api/jobs/{job_id}", ({ response }) => {
                return response(200).json(true);
            }),
        );
    });

    it("renders the job state badge with the job state text", async () => {
        const wrapper = mountJobState(BASE_JOB);
        await flushPromises();
        expect(wrapper.find(SELECTORS.STATE_BADGE).text()).toContain("running");
    });

    it("shows the stop button for a non-terminal state when using JobBaseModel (no user_id)", async () => {
        const wrapper = mountJobState({ ...BASE_JOB, state: "running" });
        await flushPromises();
        expect(wrapper.find(SELECTORS.STOP_BTN).exists()).toBe(true);
    });

    it("hides the stop button for terminal states", async () => {
        for (const state of ["ok", "error", "deleted", "failed"] as JobStateType[]) {
            const wrapper = mountJobState({ ...BASE_JOB, state });
            await flushPromises();
            expect(wrapper.find(SELECTORS.STOP_BTN).exists()).toBe(false);
        }
    });

    it("shows the stop button when ShowFullJobResponse user_id matches current user", async () => {
        const wrapper = mountJobState({ ...FULL_JOB, state: "running", user_id: FAKE_USER.id });
        await flushPromises();
        expect(wrapper.find(SELECTORS.STOP_BTN).exists()).toBe(true);
    });

    it("hides the stop button when ShowFullJobResponse user_id does not match current user", async () => {
        const wrapper = mountJobState({ ...FULL_JOB, state: "running", user_id: "someone-else" });
        await flushPromises();
        expect(wrapper.find(SELECTORS.STOP_BTN).exists()).toBe(false);
    });

    it("hides the stop button when no user is logged in", async () => {
        const wrapper = mountJobState(BASE_JOB, null);
        await flushPromises();
        expect(wrapper.find(SELECTORS.STOP_BTN).exists()).toBe(false);
    });

    it("calls DELETE /api/jobs/{job_id} when stop button is clicked", async () => {
        let deletedJobId: string | undefined;
        server.use(
            http.delete("/api/jobs/{job_id}", ({ response, params }) => {
                deletedJobId = params.job_id;
                return response(200).json(true);
            }),
        );

        const wrapper = mountJobState({ ...BASE_JOB, state: "running" });
        await flushPromises();

        await wrapper.find(SELECTORS.STOP_BTN).trigger("click");
        await flushPromises();

        expect(deletedJobId).toBe(BASE_JOB.id);
    });

    it("disables the stop button while stopping is in progress", async () => {
        let resolveDelete!: () => void;
        server.use(
            http.delete("/api/jobs/{job_id}", ({ response }) => {
                return new Promise((resolve) => {
                    resolveDelete = () => resolve(response(200).json(true));
                });
            }),
        );

        const wrapper = mountJobState({ ...BASE_JOB, state: "running" });
        await flushPromises();

        const stopBtn = wrapper.find(SELECTORS.STOP_BTN);
        stopBtn.trigger("click");
        await flushPromises();

        expect(stopBtn.classes()).toContain("g-disabled");

        resolveDelete();
        await flushPromises();

        expect(stopBtn.classes()).not.toContain("g-disabled");
    });
});
