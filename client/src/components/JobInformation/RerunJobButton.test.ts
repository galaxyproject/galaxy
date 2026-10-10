import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { ShowFullJobResponse } from "@/api/jobs";
import { type Tool, useToolStore } from "@/stores/toolStore";

import TEST_JOBS_JSON from "../WorkflowInvocationState/test/json/jobs.json";

import RerunJobButton from "./RerunJobButton.vue";

const localVue = getLocalVue();
const router = injectTestRouter(localVue);
const { server } = useServerMock();

// "sample-job-2" is terminal, so useJobDetails's polling doesn't keep a timer running past the test.
const BASE_JOB = TEST_JOBS_JSON.find((job) => job.id === "sample-job-2") as unknown as ShowFullJobResponse;

const JOB_ID = BASE_JOB.id;
const TOOL_ID = BASE_JOB.tool_id;

const RERUNNABLE_TOOL = { id: TOOL_ID, is_workflow_compatible: true } as Tool;
const NON_RERUNNABLE_TOOL = { id: TOOL_ID, is_workflow_compatible: false } as Tool;

const SELECTORS = {
    BUTTON: ".g-button",
    SPINNER: "[data-icon='spinner']",
};

function mountRerunJobButton() {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    return mount(RerunJobButton as object, {
        propsData: { jobId: JOB_ID },
        localVue,
        pinia,
        router,
    });
}

describe("RerunJobButton.vue", () => {
    beforeEach(() => {
        server.use(http.get("/api/jobs/:job_id", () => HttpResponse.json(BASE_JOB)));
    });

    afterEach(() => {
        vi.clearAllTimers();
    });

    it("renders disabled with a spinner while the tool is loading", async () => {
        server.use(http.get("/api/tools/:tool_id", () => new Promise(() => {})));

        const wrapper = mountRerunJobButton();
        await flushPromises();

        const button = wrapper.find(SELECTORS.BUTTON);
        expect(button.exists()).toBe(true);
        expect(button.classes()).toContain("g-disabled");
        expect(wrapper.find(SELECTORS.SPINNER).exists()).toBe(true);
    });

    it("enables the button once the tool is loaded and is workflow-compatible", async () => {
        server.use(http.get("/api/tools/:tool_id", () => HttpResponse.json(RERUNNABLE_TOOL)));

        const wrapper = mountRerunJobButton();
        await flushPromises();

        expect(wrapper.find(SELECTORS.BUTTON).classes()).not.toContain("g-disabled");
    });

    it("stays disabled once loaded if the tool is not workflow-compatible", async () => {
        server.use(http.get("/api/tools/:tool_id", () => HttpResponse.json(NON_RERUNNABLE_TOOL)));

        const wrapper = mountRerunJobButton();
        await flushPromises();

        expect(wrapper.find(SELECTORS.BUTTON).classes()).toContain("g-disabled");
    });

    it("does not re-fetch the tool if it's already cached in the store", async () => {
        let toolFetchCount = 0;
        server.use(
            http.get("/api/tools/:tool_id", () => {
                toolFetchCount++;
                return HttpResponse.json(RERUNNABLE_TOOL);
            }),
        );

        const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        const toolStore = useToolStore();
        toolStore.fetchToolForId(TOOL_ID);
        await flushPromises();
        expect(toolFetchCount).toBe(1);

        const wrapper = mount(RerunJobButton as object, {
            propsData: { jobId: JOB_ID },
            localVue,
            pinia,
            router,
        });
        await flushPromises();

        expect(toolFetchCount).toBe(1);
        expect(wrapper.find(SELECTORS.BUTTON).classes()).not.toContain("g-disabled");
    });
});
