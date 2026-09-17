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
import ToolSuccessOutputs from "./ToolSuccessOutputs.vue";
import JobHeader from "@/components/JobInformation/JobHeader.vue";
import JobState from "@/components/JobStates/JobState.vue";

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(),
}));

vi.mock("axios", () => ({
    default: {
        get: vi.fn().mockResolvedValue({ data: [] }),
    },
}));

vi.mock("@/stores/toolStore", () => ({
    useToolStore: () => ({
        getToolNameById: () => TEST_TOOL_NAME,
    }),
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
    PAGINATION_ITEM: ".page-item .page-link",
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
            JobState: true,
            RerunJobButton: true,
            Webhook: true,
            ToolRecommendation: true,
            ToolSuccessOutputs: true,
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

        it("renders JobHeader for the job with tool name", () => {
            const jobHeader = wrapper.findComponent(JobHeader);
            expect(jobHeader.text()).toContain(TEST_TOOL_NAME);
            expect(jobHeader.props("jobId")).toEqual(jobInformationResponse.id);
        });

        it("does not show the multi-job pagination header", () => {
            expect(wrapper.findAll(SELECTORS.PAGINATION_ITEM).length).toBe(0);
        });
    });

    describe("with outputs", () => {
        const TEST_OUTPUT = { id: "output_id", hid: 1, name: "output1" };
        const TEST_OUTPUT_COLLECTION = { id: "collection_id", hid: 2, name: "collection1" };

        it("passes both dataset and collection outputs through to ToolSuccessOutputs", async () => {
            const wrapper = await mountToolSuccess({
                jobDef: TEST_JOB_DEF,
                jobResponse: {
                    ...TEST_JOB_RESPONSE,
                    outputs: [TEST_OUTPUT],
                    output_collections: [TEST_OUTPUT_COLLECTION],
                },
                toolName: TEST_TOOL_NAME,
            });

            const outputs = wrapper.findComponent(ToolSuccessOutputs);
            expect(outputs.exists()).toBe(true);
            expect(outputs.props("jobResponse").outputs).toEqual([TEST_OUTPUT]);
            expect(outputs.props("jobResponse").output_collections).toEqual([TEST_OUTPUT_COLLECTION]);
        });
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

        it("shows a pagination control for each job", () => {
            expect(wrapper.findAll(SELECTORS.PAGINATION_ITEM).length).toBeGreaterThan(0);
        });

        it("shows JobState and RerunJobButton for the currently viewed job", () => {
            const jobState = wrapper.findComponent(JobState);
            expect(jobState.exists()).toBe(true);
            expect(jobState.props("jobId")).toEqual(jobInformationResponse.id);
        });

        it("switches the viewed job when navigating to the next pagination page", async () => {
            const pageTwo = wrapper
                .findAll(SELECTORS.PAGINATION_ITEM)
                .filter((link) => link.text() === "2")
                .at(0);
            await pageTwo.trigger("click");

            const jobState = wrapper.findComponent(JobState);
            expect(jobState.props("jobId")).toEqual(SECOND_JOB.id);
        });
    });
});
