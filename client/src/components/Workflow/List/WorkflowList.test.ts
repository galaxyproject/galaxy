import { createTestingPinia, type TestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getFakeWorkflowSummary } from "@tests/test-data/workflows";
import {
    createTestRouter,
    expectConfigurationRequest,
    getLocalVue,
    suppressBootstrapVueWarnings,
    withPlugins,
} from "@tests/vitest/helpers";
import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { loadWorkflows, type WorkflowSummary } from "@/api/workflows";
import { useUserStore } from "@/stores/userStore";

import WorkflowList from "./WorkflowList.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const { server, http } = useServerMock();

vi.mock("@/api/workflows", () => ({
    loadWorkflows: vi.fn(),
}));

const mockedLoadWorkflows = vi.mocked(loadWorkflows);

const localVue = getLocalVue();
const router = createTestRouter();

const FAKE_USERNAME = "fake_username";
const FAKE_USER = getFakeRegisteredUser({
    id: "fake_user_id",
    email: "fake_user_email",
    username: FAKE_USERNAME,
});

const SELECTORS = {
    WORKFLOW_CARD: ".workflow-card",
    EMPTY_LIST: "#workflow-list-empty",
    FILTER_INPUT: "#workflow-list-filter input",
    SHOW_DELETED_BUTTON: "#show-deleted",
};

/** Workflows owned by the fake user, served as the list's only page. */
function serveWorkflows(count: number, overrides: Partial<WorkflowSummary> = {}) {
    const workflows = Array.from({ length: count }, (_, i) =>
        getFakeWorkflowSummary({ id: `workflow-${i}`, name: `Workflow ${i}`, owner: FAKE_USERNAME, ...overrides }),
    );
    mockedLoadWorkflows.mockResolvedValue({ data: workflows, totalMatches: count });
    return workflows;
}

/** Mounts the list before any user has loaded; the "my" list waits for one. */
function mountWorkflowList(pinia: TestingPinia = createTestingPinia({ createSpy: vi.fn, stubActions: false })) {
    setActivePinia(pinia);
    const wrapper = mount(WorkflowList, { global: withPlugins(localVue, pinia, router) });
    return { wrapper, userStore: useUserStore() };
}

async function mountWorkflowListForUser() {
    const { wrapper, userStore } = mountWorkflowList();
    userStore.currentUser = FAKE_USER;
    await flushPromises();
    return wrapper;
}

function filterText(wrapper: VueWrapper) {
    return wrapper.find<HTMLInputElement>(SELECTORS.FILTER_INPUT).element.value;
}

enableAutoUnmount(afterEach);

describe("WorkflowList", () => {
    beforeEach(() => {
        suppressBootstrapVueWarnings();
        vi.clearAllMocks();
        server.use(
            // Workflow card badges request their counts.
            http.get("/api/workflows/{workflow_id}/counts", ({ response }) => {
                return response(200).json({});
            }),
            // The tab bar reads useConfig(), and the configuration store fetches in its setup body.
            expectConfigurationRequest(http, {}),
        );
    });

    it("shows the empty-list message when there are no workflows", async () => {
        serveWorkflows(0);
        const wrapper = await mountWorkflowListForUser();

        expect(wrapper.findAll(SELECTORS.WORKFLOW_CARD)).toHaveLength(0);
        expect(wrapper.find(SELECTORS.EMPTY_LIST).exists()).toBe(true);
    });

    it("renders a card for each workflow", async () => {
        const workflows = serveWorkflows(10);
        const wrapper = await mountWorkflowListForUser();

        expect(wrapper.findAll(SELECTORS.WORKFLOW_CARD)).toHaveLength(10);
        expect(wrapper.find(SELECTORS.EMPTY_LIST).exists()).toBe(false);

        const nonDeletedWorkflows = workflows.filter((w) => !w.deleted);
        expect(wrapper.findAll(SELECTORS.WORKFLOW_CARD)).toHaveLength(nonDeletedWorkflows.length);
    });

    it("renders own workflows when the user loads after the workflow list", async () => {
        serveWorkflows(3);
        const { wrapper, userStore } = mountWorkflowList(createTestingPinia({ createSpy: vi.fn }));
        await flushPromises();

        expect(wrapper.findAll(SELECTORS.WORKFLOW_CARD)).toHaveLength(0);
        expect(wrapper.findComponent(LoadingSpan).exists()).toBe(true);
        expect(wrapper.find(SELECTORS.EMPTY_LIST).exists()).toBe(false);

        userStore.currentUser = FAKE_USER;
        await flushPromises();

        expect(wrapper.findAll(SELECTORS.WORKFLOW_CARD)).toHaveLength(3);
        expect(wrapper.findComponent(LoadingSpan).exists()).toBe(false);
    });

    it("toggles the is:deleted filter with the show-deleted button", async () => {
        serveWorkflows(10, { deleted: true });
        const wrapper = await mountWorkflowListForUser();

        expect(filterText(wrapper)).toBe("");
        expect(wrapper.find(SELECTORS.SHOW_DELETED_BUTTON).exists()).toBe(true);

        await wrapper.find(SELECTORS.SHOW_DELETED_BUTTON).trigger("click");

        expect(filterText(wrapper)).toBe("is:deleted");
        expect(wrapper.find(SELECTORS.SHOW_DELETED_BUTTON).exists()).toBe(true);

        await wrapper.find(SELECTORS.SHOW_DELETED_BUTTON).trigger("click");

        expect(filterText(wrapper)).toBe("");
    });
});
