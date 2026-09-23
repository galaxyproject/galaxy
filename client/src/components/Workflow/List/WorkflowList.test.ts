import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, suppressBootstrapVueWarnings } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import VueRouter from "vue-router";

import { useServerMock } from "@/api/client/__mocks__";
import { loadWorkflows } from "@/api/workflows";
import { type Tool, useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";

import { generateRandomWorkflowList } from "../testUtils";

import WorkflowList from "./WorkflowList.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";

const { server, http } = useServerMock();

vi.mock("@/api/workflows", () => ({
    loadWorkflows: vi.fn(),
}));

const mockedLoadWorkflows = loadWorkflows as ReturnType<typeof vi.fn>;

const localVue = getLocalVue();
localVue.use(VueRouter);
const router = new VueRouter();

const FAKE_USER_ID = "fake_user_id";
const FAKE_USERNAME = "fake_username";
const FAKE_USER_EMAIL = "fake_user_email";
const FAKE_USER = getFakeRegisteredUser({
    id: FAKE_USER_ID,
    email: FAKE_USER_EMAIL,
    username: FAKE_USERNAME,
});

async function mountWorkflowList() {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);

    useToolStore().saveAllTools([
        { id: "cut1", name: "Cut" },
        { id: "adv_cut1", name: "Advanced Cut" },
        { id: "cat1", name: "Concatenate datasets" },
    ] as unknown as Tool[]);

    const wrapper = mount(WorkflowList as object, {
        localVue,
        pinia,
        router,
    });

    const userStore = useUserStore();
    userStore.currentUser = FAKE_USER;

    await flushPromises();

    return wrapper;
}

/** Simulates a user typing `filterText` into the filter box and waits for the resulting `load()` call. */
async function search(wrapper: ReturnType<typeof mount>, filterText: string) {
    const filterMenu = wrapper.findComponent(FilterMenu);
    filterMenu.vm.$emit("update:filter-text", filterText);
    await flushPromises();
}

/** Returns the `search`/`filterText` value most recently sent to the backend via `loadWorkflows`. */
function lastSearchSent() {
    const lastCall = mockedLoadWorkflows.mock.calls[mockedLoadWorkflows.mock.calls.length - 1];
    return lastCall?.[0]?.filterText;
}

describe("WorkflowList", () => {
    beforeEach(() => {
        suppressBootstrapVueWarnings();
        vi.clearAllMocks();
        // Mock the workflow counts endpoint used by workflow card badges
        server.use(
            http.get("/api/workflows/{workflow_id}/counts", ({ response }) => {
                return response(200).json({});
            }),
        );
    });

    it("render empty workflow list", async () => {
        mockedLoadWorkflows.mockResolvedValue({ data: [], totalMatches: 0 });
        const wrapper = await mountWorkflowList();

        expect(wrapper.findAll(".workflow-card")).toHaveLength(0);
        expect(wrapper.find("#workflow-list-empty").exists()).toBe(true);
    });

    it("render workflow list", async () => {
        const FAKE_WORKFLOWS = generateRandomWorkflowList(FAKE_USERNAME, 10);
        mockedLoadWorkflows.mockResolvedValue({ data: FAKE_WORKFLOWS, totalMatches: 10 });
        const wrapper = await mountWorkflowList();

        expect(wrapper.findAll(".workflow-card")).toHaveLength(10);
        expect(wrapper.find("#workflow-list-empty").exists()).toBe(false);

        const nonDeletedWorkflows = FAKE_WORKFLOWS.filter((w) => !w.deleted);
        expect(wrapper.findAll(".workflow-card")).toHaveLength(nonDeletedWorkflows.length);
    });

    it("toggle show deleted workflows", async () => {
        const FAKE_WORKFLOWS = generateRandomWorkflowList(FAKE_USERNAME, 10);
        FAKE_WORKFLOWS.forEach((w) => (w.deleted = true));
        mockedLoadWorkflows.mockResolvedValue({ data: FAKE_WORKFLOWS, totalMatches: 10 });
        const wrapper = await mountWorkflowList();

        expect((wrapper.find("#workflow-list-filter input").element as HTMLInputElement).value).toBe("");

        const showDeletedButton = wrapper.find("#show-deleted");
        expect(showDeletedButton.exists()).toBe(true);
        showDeletedButton.trigger("click");

        await wrapper.vm.$nextTick();

        expect((wrapper.find("#workflow-list-filter input").element as HTMLInputElement).value).toBe("is:deleted");

        expect(showDeletedButton.exists()).toBe(true);
        showDeletedButton.trigger("click");

        await wrapper.vm.$nextTick();

        expect((wrapper.find("#workflow-list-filter input").element as HTMLInputElement).value).toBe("");
        await flushPromises();
    });
});

describe("WorkflowList filtering", () => {
    beforeEach(() => {
        suppressBootstrapVueWarnings();
        vi.clearAllMocks();
        // Mock the workflow counts endpoint used by workflow card badges
        server.use(
            http.get("/api/workflows/{workflow_id}/counts", ({ response }) => {
                return response(200).json({});
            }),
        );
        mockedLoadWorkflows.mockResolvedValue({ data: generateRandomWorkflowList(FAKE_USERNAME, 1), totalMatches: 1 });
    });

    it("sends a plain-text search as-is", async () => {
        const wrapper = await mountWorkflowList();

        await search(wrapper, "my workflow name");

        expect(lastSearchSent()).toBe("my workflow name");
    });

    it("sends a name: filter as-is", async () => {
        const wrapper = await mountWorkflowList();

        await search(wrapper, "name:'My Workflow'");

        expect(lastSearchSent()).toBe("name:'My Workflow'");
    });

    it("sends a tag: filter as-is", async () => {
        const wrapper = await mountWorkflowList();

        await search(wrapper, "tag:'my-tag'");

        expect(lastSearchSent()).toBe("tag:'my-tag'");
    });

    it("sends a tool_id: filter as-is", async () => {
        const wrapper = await mountWorkflowList();

        await search(wrapper, "tool_id:cut1");

        expect(lastSearchSent()).toBe("tool_id:cut1");
    });

    it("resolves a tool_name: filter to the matching tool_id before sending", async () => {
        const wrapper = await mountWorkflowList();

        await search(wrapper, "tool_name:'Cut' tag:my-tag");

        const sent = lastSearchSent();
        expect(sent).toEqual("tag:my-tag tool_id:cut1");
        expect(sent).not.toContain("tool_name");
    });

    it("does not resolve tool_name to tool_id when no tool matches", async () => {
        const wrapper = await mountWorkflowList();

        await search(wrapper, "tool_name:'nonexistent tool'");

        const sent = lastSearchSent();
        expect(sent).not.toContain("tool_id:");
        expect(sent).toContain("tool_name");
    });

    it("combines multiple filters into one search string", async () => {
        const wrapper = await mountWorkflowList();

        await search(wrapper, "name:'My Workflow' tag:'my-tag'");

        const sent = lastSearchSent();
        expect(sent).toContain("name:'My Workflow'");
        expect(sent).toContain("tag:'my-tag'");
    });
});
