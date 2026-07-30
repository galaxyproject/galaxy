import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getWorkflowInfo } from "@/api/workflows";

import WorkflowEditor from "./WorkflowEditor.vue";
import Index from "@/components/Workflow/Editor/Index.vue";

const localVue = getLocalVue(true);

vi.mock("@/api/workflows", () => ({
    getWorkflowInfo: vi.fn(),
}));

const mockedGetWorkflowInfo = getWorkflowInfo as ReturnType<typeof vi.fn>;

beforeEach(() => {
    mockedGetWorkflowInfo.mockReset();
});

/**
 * `WorkflowEditor` reads the id/version params from `window.location.search`
 * directly (see `@/utils/query-string-parsing`); `$route.query` is only used
 * to trigger a re-parse of the URL, so both need to be set for each scenario.
 */
function setLocationSearch(search: string) {
    Object.defineProperty(window.location, "search", {
        configurable: true,
        writable: true,
        value: search,
    });
}

async function mountWorkflowEditor(search = "") {
    setLocationSearch(search);
    const query = Object.fromEntries(new URLSearchParams(search));

    const wrapper = shallowMount(WorkflowEditor as object, {
        localVue,
        mocks: {
            $route: { query },
        },
    });
    await flushPromises();
    return wrapper;
}

describe("WorkflowEditor", () => {
    it("renders Editor for a new workflow (no workflow-id) when no id is present in the query", async () => {
        const wrapper = await mountWorkflowEditor("");

        const editor = wrapper.findComponent(Index);
        expect(editor.exists()).toBe(true);
        expect(editor.props("workflowId")).toBeFalsy();
    });

    it("renders Editor with the stored workflow id from the query string", async () => {
        const wrapper = await mountWorkflowEditor("?id=stored123");

        expect(mockedGetWorkflowInfo).not.toHaveBeenCalled();

        const editor = wrapper.findComponent(Index);
        expect(editor.exists()).toBe(true);
        expect(editor.props("workflowId")).toBe("stored123");
    });

    it("resolves the workflow id via getWorkflowInfo when only workflow_id is present", async () => {
        mockedGetWorkflowInfo.mockResolvedValueOnce({ id: "resolved789" });

        const wrapper = await mountWorkflowEditor("?workflow_id=instance456");

        expect(mockedGetWorkflowInfo).toHaveBeenCalledWith("instance456", undefined, true);

        const editor = wrapper.findComponent(Index);
        expect(editor.props("workflowId")).toBe("resolved789");
    });

    it("parses the version query parameter as an integer and passes it to Editor", async () => {
        const wrapper = await mountWorkflowEditor("?id=stored123&version=3");

        const editor = wrapper.findComponent(Index);
        expect(editor.props("initialVersion")).toBe(3);
    });

    it("remounts Editor (forces a reload) when it emits forceReload", async () => {
        const wrapper = await mountWorkflowEditor("");

        const editorBefore = wrapper.findComponent(Index);
        expect(editorBefore.exists()).toBe(true);

        editorBefore.vm.$emit("forceReload");
        await flushPromises();

        const editorAfter = wrapper.findComponent(Index);
        expect(editorAfter.exists()).toBe(true);
        // A new Editor instance means the `:key` changed and it was remounted.
        expect(editorAfter.vm).not.toBe(editorBefore.vm);
    });

    it("re-emits update:confirmation from the Editor", async () => {
        const wrapper = await mountWorkflowEditor("");

        wrapper.findComponent(Index).vm.$emit("update:confirmation", true);

        expect(wrapper.emitted("update:confirmation")).toBeTruthy();
        expect(wrapper.emitted("update:confirmation")?.[0]).toEqual([true]);
    });
});
