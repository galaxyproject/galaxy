import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { reactive } from "vue";

import { getWorkflowInfo } from "@/api/workflows";

import WorkflowEditor from "./WorkflowEditor.vue";
import Index from "@/components/Workflow/Editor/Index.vue";

const localVue = getLocalVue(true);

// A reactive route stub: vue-router's real `route.query` is reactive
let mockRoute = reactive<{ path: string; query: Record<string, string> }>({ path: "/", query: {} });

vi.mock("vue-router/composables", () => ({
    useRoute: () => mockRoute,
}));

vi.mock("@/api/workflows", () => ({
    getWorkflowInfo: vi.fn(),
}));

const mockedGetWorkflowInfo = getWorkflowInfo as ReturnType<typeof vi.fn>;

beforeEach(() => {
    mockRoute = reactive({ path: "/", query: {} });
    vi.clearAllMocks();
});

function setQuery(search: string) {
    mockRoute.query = Object.fromEntries(new URLSearchParams(search));
}

async function mountWorkflowEditor(search = "") {
    setQuery(search);

    const wrapper = shallowMount(WorkflowEditor as object, { localVue });
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
        mockedGetWorkflowInfo.mockResolvedValueOnce({ id: "resolved789", tags: ["tag1"] });

        const wrapper = await mountWorkflowEditor("?workflow_id=instance456");

        expect(mockedGetWorkflowInfo).toHaveBeenCalledWith("instance456", undefined, true);

        const editor = wrapper.findComponent(Index);
        expect(editor.props("workflowId")).toBe("resolved789");
        expect(editor.props("workflowTags")).toEqual(["tag1"]);
    });

    it("leaves initialVersion undefined when no version query parameter is present", async () => {
        const wrapper = await mountWorkflowEditor("?id=stored123");

        const editor = wrapper.findComponent(Index);
        expect(editor.props("initialVersion")).toBeUndefined();
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

    it("reloads the editor config when the query changes in place (switching workflows without remounting)", async () => {
        const wrapper = await mountWorkflowEditor("?id=stored123");

        const editorBefore = wrapper.findComponent(Index);
        expect(editorBefore.props("workflowId")).toBe("stored123");

        // Mutate the same route.query object in place, as vue-router does when
        // navigating to a new workflow while already inside the editor.
        mockRoute.query.id = "stored456";
        await flushPromises();

        const editorAfter = wrapper.findComponent(Index);
        expect(editorAfter.props("workflowId")).toBe("stored456");
        // The `:key` bump also means it's a fresh Editor instance.
        expect(editorAfter.vm).not.toBe(editorBefore.vm);
    });

    it("re-emits update:confirmation from the Editor", async () => {
        const wrapper = await mountWorkflowEditor("");

        wrapper.findComponent(Index).vm.$emit("update:confirmation", true);

        expect(wrapper.emitted("update:confirmation")).toBeTruthy();
        expect(wrapper.emitted("update:confirmation")?.[0]).toEqual([true]);
    });
});
