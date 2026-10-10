import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import type { AnyHistory } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { useHistoryStore } from "@/stores/historyStore";

import WorkflowAnnotation from "./WorkflowAnnotation.vue";

const localVue = getLocalVue();
const { server, http } = useServerMock();

const WORKFLOW_OWNER = "test-user";
const OTHER_USER = "other-user";
const WORKFLOW_UPDATE_TIME = "2023-01-01T00:00:00.000Z";
const INVOCATION_TIME = "2024-01-01T00:00:00.000Z";
const OWN_WORKFLOW = {
    id: "workflow-id",
    name: "workflow-name",
    owner: WORKFLOW_OWNER,
    version: 1,
    update_time: WORKFLOW_UPDATE_TIME,
};
const PUBLISHED_WORKFLOW = { ...OWN_WORKFLOW, id: "published-workflow-id", published: true };
const SAMPLE_RUN_COUNT = 100;
const TEST_HISTORY = {
    id: "test-history-id",
    genome_build: "?",
    name: "fake-history-name",
};

const SELECTORS = {
    RUN_COUNT: ".workflow-invocations-count",
    INDICATORS_LINK: '[data-description="published owner badge"]',
    SWITCH_TO_HISTORY_LINK: "[data-description='switch to history link']",
    CURRENT_HISTORY_INDICATOR: "[data-description='current history indicator']",
    TIME_INFO: '[data-description="workflow annotation time info"]',
    DATE: '[data-description="workflow annotation date"]',
};

type View = "run_form" | "invocation";
const VIEWS: View[] = ["run_form", "invocation"];

/**
 * Mounts the annotation in the run form or invocation view for a stored workflow, with
 * `TEST_HISTORY` as the current history.
 * By default the current user owns the workflow; otherwise another user views
 * `PUBLISHED_WORKFLOW`, which is published by `WORKFLOW_OWNER`.
 */
async function mountWorkflowAnnotation(view: View, { owned = true } = {}) {
    server.use(
        http.get("/api/histories/{history_id}", ({ response }) => response(200).json(TEST_HISTORY)),
        http.get("/api/workflows/{workflow_id}/counts", ({ response }) =>
            response(200).json({ scheduled: SAMPLE_RUN_COUNT }),
        ),
    );
    const workflow = owned ? OWN_WORKFLOW : PUBLISHED_WORKFLOW;
    const pinia = createTestingPinia({
        createSpy: vi.fn,
        stubActions: false,
        initialState: {
            workflowStore: { workflowsByInstanceId: { [workflow.id]: workflow } },
            userStore: {
                currentUser: getFakeRegisteredUser({ username: owned ? WORKFLOW_OWNER : OTHER_USER }),
            },
        },
    });
    const historyStore = useHistoryStore(pinia);
    historyStore.setCurrentHistoryId(TEST_HISTORY.id);

    const wrapper = mount(WorkflowAnnotation, {
        props: {
            workflowId: workflow.id,
            historyId: TEST_HISTORY.id,
            invocationCreateTime: view === "invocation" ? INVOCATION_TIME : undefined,
            showDetails: view === "run_form",
        },
        global: { ...withPlugins(localVue, pinia), stubs: { ...localVue.stubs, FontAwesomeIcon: true } },
    });
    // The current history reaches the store while the history link's own request for it is in flight.
    historyStore.setHistory(TEST_HISTORY as AnyHistory);
    await flushPromises();
    return wrapper;
}

describe("WorkflowAnnotation", () => {
    it.each(VIEWS)(
        "shows the run count but no published owner badge for the user's own workflow in the %s view",
        async (view) => {
            const wrapper = await mountWorkflowAnnotation(view);

            const runCount = wrapper.find(SELECTORS.RUN_COUNT);
            expect(runCount.text()).toContain("workflow runs:");
            expect(runCount.text()).toContain(SAMPLE_RUN_COUNT.toString());
            expect(wrapper.find(SELECTORS.INDICATORS_LINK).exists()).toBe(false);
        },
    );

    it("does not link the target history in the run form view", async () => {
        const wrapper = await mountWorkflowAnnotation("run_form");

        expect(wrapper.find(SELECTORS.SWITCH_TO_HISTORY_LINK).exists()).toBe(false);
    });

    it("links the current target history by name in the invocation view", async () => {
        const wrapper = await mountWorkflowAnnotation("invocation");

        expect(wrapper.find(SELECTORS.SWITCH_TO_HISTORY_LINK).text()).toContain(TEST_HISTORY.name);
        expect(wrapper.find(SELECTORS.CURRENT_HISTORY_INDICATOR).exists()).toBe(true);
    });

    it.each(VIEWS)("shows the published owner badge for another user's workflow in the %s view", async (view) => {
        const wrapper = await mountWorkflowAnnotation(view, { owned: false });

        const indicatorsLink = wrapper.find(SELECTORS.INDICATORS_LINK);
        expect(indicatorsLink.text()).toBe(WORKFLOW_OWNER);
        expect(indicatorsLink.attributes("title")).toContain(`Published by '${WORKFLOW_OWNER}'`);
    });

    it("shows the time since the workflow was edited in the run form view", async () => {
        const wrapper = await mountWorkflowAnnotation("run_form");

        const timeInfo = wrapper.find(SELECTORS.TIME_INFO);
        expect(timeInfo.text()).toContain("edited");
        expect(timeInfo.find(SELECTORS.DATE).attributes("title")).toBe(WORKFLOW_UPDATE_TIME);
    });

    it("shows the time since the invocation in the invocation view", async () => {
        const wrapper = await mountWorkflowAnnotation("invocation");

        const timeInfo = wrapper.find(SELECTORS.TIME_INFO);
        expect(timeInfo.text()).toContain("invoked");
        expect(timeInfo.find(SELECTORS.DATE).attributes("title")).toBe(INVOCATION_TIME);
    });
});
