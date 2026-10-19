import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import type { ShowFullJobResponse } from "@/api/jobs";
import { useJobStore } from "@/stores/jobStore";
import { useUserStore } from "@/stores/userStore";

import JobPanel from "./JobPanel.vue";

const { server, http } = useServerMock();

const localVue = getLocalVue();
const router = injectTestRouter(localVue);

function buildJob(overrides: Partial<ShowFullJobResponse> = {}): ShowFullJobResponse {
    return {
        id: "job1",
        state: "ok",
        model_class: "Job",
        create_time: "2024-01-01T00:00:00",
        update_time: "2024-01-01T00:00:00",
        inputs: {},
        outputs: {},
        output_collections: {},
        params: {},
        tool_id: "cat1",
        ...overrides,
    } as ShowFullJobResponse;
}

describe("JobPanel", () => {
    let wrapper: VueWrapper;

    beforeEach(() => {
        setActivePinia(createPinia());
        server.use(
            http.get("/api/jobs", ({ response }) => {
                return response(200).json([]);
            }),
        );

        const userStore = useUserStore();
        userStore.currentUser = getFakeRegisteredUser({ id: "fakeUser", email: "fake_user_email" });

        wrapper = mount(JobPanel as object, {
            localVue,
            router,
        });
    });

    it("shows a job that lands in jobStore via another view while no filter is active", async () => {
        await flushPromises();

        const jobStore = useJobStore();
        jobStore.updateJob("job1", buildJob());
        await flushPromises();

        expect(wrapper.text()).toContain("cat1");
    });

    it("does not show a job belonging to another user (by user_id)", async () => {
        await flushPromises();

        const jobStore = useJobStore();
        jobStore.updateJob("job1", buildJob({ user_id: "otherUser" }));
        await flushPromises();

        expect(wrapper.text()).not.toContain("cat1");
    });

    it("does not show a job belonging to another user (by user_email)", async () => {
        await flushPromises();

        const jobStore = useJobStore();
        jobStore.updateJob("job1", buildJob({ user_email: "someone_else@example.com" }));
        await flushPromises();

        expect(wrapper.text()).not.toContain("cat1");
    });

    it("shows a job with no owner information (the common, non-admin case)", async () => {
        await flushPromises();

        const jobStore = useJobStore();
        jobStore.updateJob("job1", buildJob({ user_id: null, user_email: null }));
        await flushPromises();

        expect(wrapper.text()).toContain("cat1");
    });
});
