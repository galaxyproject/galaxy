import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { computed } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import type { JobRequest } from "@/api/jobs";
import jobInformationResponse from "@/components/JobInformation/testData/jobInformationResponse.json";
import { useConfig } from "@/composables/config";

import ToolSuccess from "./ToolSuccess.vue";
import JobHeader from "@/components/JobInformation/JobHeader.vue";

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(),
}));

vi.mock("axios", () => ({
    default: {
        get: vi.fn().mockResolvedValue({ data: [] }),
    },
}));

const { server, http } = useServerMock();

beforeEach(() => {
    server.use(
        http.get("/api/invocations", ({ response }) => response(200).json([])),
        http.get("/api/jobs/{job_id}", ({ response, params }) =>
            response(200).json({ ...jobInformationResponse, id: params.job_id, state: "ok" } as never),
        ),
        http.get("/api/jobs/{job_id}/console_output", ({ response }) =>
            response(200).json({ stdout: "", stderr: "", state: "ok" }),
        ),
    );
});

const localVue = getLocalVue();
const router = injectTestRouter(localVue);

vi.mocked(useConfig).mockReturnValue({
    config: computed(() => ({ enable_tool_recommendations: false })),
    isConfigLoaded: computed(() => true),
});

const TEST_TOOL_NAME = "Test Tool";

const TEST_JOB_DEF = {
    tool_id: "test_tool",
} as JobRequest;

const TEST_JOB_RESPONSE = {
    produces_entry_points: false,
    jobs: [jobInformationResponse],
    outputs: [],
    output_collections: [],
};

// Selectors
const SELECTORS = {
    JOB_COUNT_BADGE: ".tool-success-job-count",
    JOB_DROPDOWN_ITEM: ".job-selection-dropdown .dropdown-item",
};

async function mountToolSuccess(latestResponse: Record<string, unknown> | null) {
    const testPinia = createTestingPinia({
        createSpy: vi.fn,
        stubActions: false,
        initialState: {
            jobStore: {
                latestResponse,
            },
        },
    });
    setActivePinia(testPinia);

    const wrapper = mount(ToolSuccess as object, {
        localVue,
        router,
        pinia: testPinia,
        stubs: {
            FontAwesomeIcon: true,
            JobHeader: true,
            Webhook: true,
            ToolRecommendation: true,
        },
    }) as Wrapper<Vue>;

    await flushPromises();
    return wrapper;
}

describe("ToolSuccess", () => {
    it("redirects home when there is no response in the store", async () => {
        const routerPush = vi.spyOn(router, "push");
        await mountToolSuccess(null);
        expect(routerPush).toHaveBeenCalledWith("/");
    });

    describe("with a single job", () => {
        let wrapper: Wrapper<Vue>;

        beforeEach(async () => {
            wrapper = await mountToolSuccess({
                jobDef: TEST_JOB_DEF,
                jobResponse: TEST_JOB_RESPONSE,
                toolName: TEST_TOOL_NAME,
            });
        });

        it("renders a single, non-minimal JobHeader for the job", () => {
            const jobHeader = wrapper.findComponent(JobHeader);
            expect(jobHeader.exists()).toBe(true);
            expect(jobHeader.props("jobId")).toEqual(jobInformationResponse.id);
            expect(jobHeader.props("minimal")).toBe(false);
        });

        it("does not show the multi-job header or job count badge", () => {
            expect(wrapper.find(SELECTORS.JOB_COUNT_BADGE).exists()).toBe(false);
        });

        // TODO: Add testing for rendering outputs
        // it("shows both dataset and collection outputs correctly", async () => {
    });

    describe("with multiple jobs", () => {
        const SECOND_JOB = { ...jobInformationResponse, id: "test_id_2" };
        let wrapper: Wrapper<Vue>;

        beforeEach(async () => {
            wrapper = await mountToolSuccess({
                jobDef: TEST_JOB_DEF,
                jobResponse: {
                    ...TEST_JOB_RESPONSE,
                    jobs: [jobInformationResponse, SECOND_JOB],
                },
                toolName: TEST_TOOL_NAME,
            });
        });

        it("shows the tool name and job count", () => {
            expect(wrapper.text()).toContain(TEST_TOOL_NAME);
            expect(wrapper.find(SELECTORS.JOB_COUNT_BADGE).text()).toContain("2 Jobs Submitted");
        });

        it("has an entry in the job picker dropdown for each job", () => {
            expect(wrapper.findAll(SELECTORS.JOB_DROPDOWN_ITEM).length).toBe(2);
        });

        it("renders a single, minimal JobHeader for the currently viewed job", () => {
            const jobHeader = wrapper.findComponent(JobHeader);
            expect(jobHeader.exists()).toBe(true);
            expect(jobHeader.props("jobId")).toEqual(jobInformationResponse.id);
            expect(jobHeader.props("minimal")).toBe(true);
        });

        it("switches the viewed job when navigating to the next job", async () => {
            const nextButton = wrapper
                .findAll("button")
                .filter((btn) => btn.text().includes("Next"))
                .at(0);
            await nextButton.trigger("click");

            const jobHeader = wrapper.findComponent(JobHeader);
            expect(jobHeader.props("jobId")).toEqual(SECOND_JOB.id);
        });
    });
});
