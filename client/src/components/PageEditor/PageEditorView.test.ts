import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import type { Pinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type Vue from "vue";
import { ref } from "vue";

import type { HistoryPageDetails, PageRevisionDetails, PageRevisionSummary } from "@/api/pages";
import { usePageEditorStore } from "@/stores/pageEditorStore";

import GModal from "../BaseComponents/GModal.vue";
import PageDisplayOnly from "./PageDisplayOnly.vue";
import PageDisplayToolbar from "./PageDisplayToolbar.vue";
import PageEditorView from "./PageEditorView.vue";
import PageRevisionList from "./PageRevisionList.vue";
import PageRevisionView from "./PageRevisionView.vue";
import MarkdownEditor from "@/components/Markdown/MarkdownEditor.vue";

const mockConfig = ref<Record<string, unknown> | null>({ llm_api_configured: true });

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(() => ({
        config: mockConfig,
        isConfigLoaded: ref(true),
    })),
}));

const mockPush = vi.fn();
vi.mock("vue-router/composables", () => ({
    useRouter: vi.fn(() => ({
        push: mockPush,
    })),
    useRoute: vi.fn(() => ({
        params: {},
    })),
}));

vi.mock("@/stores/historyStore", () => ({
    useHistoryStore: vi.fn(() => ({
        getHistoryById: vi.fn((id: string) => {
            if (id === "history-1") {
                return { id: "history-1", name: "Test History" };
            }
            return undefined;
        }),
    })),
}));

vi.mock("@/stores/userStore", () => ({
    useUserStore: vi.fn(() => ({
        matchesCurrentUsername: vi.fn((username: string) => username === "test-owner"),
    })),
}));

vi.mock("@/composables/confirmDialog.js", () => ({
    useConfirmDialog: vi.fn(() => ({
        confirm: vi.fn().mockResolvedValue(true),
    })),
}));

const mockGalaxyInstance = { frame: { active: false } };
vi.mock("@/app", () => ({
    getGalaxyInstance: vi.fn(() => mockGalaxyInstance),
}));

const localVue = getLocalVue();

const HISTORY_ID = "history-1";
const PAGE_ID = "page-1";

let pinia: Pinia;

function mountComponent(propsData: { pageId: string; historyId?: string; displayOnly?: boolean }) {
    return shallowMount(PageEditorView as object, {
        localVue,
        propsData,
        pinia,
    });
}

function setupLoadedPage(historyId?: string) {
    const store = usePageEditorStore();
    store.isLoadingList = false;
    store.isLoadingPage = false;
    store.error = null;
    store.currentPage = {
        id: PAGE_ID,
        history_id: historyId || null,
        title: "My Page",
        content: "# Hello",
        update_time: "2024-01-01T00:00:00",
        username: "test-owner",
    } as Partial<HistoryPageDetails> as HistoryPageDetails;
    store.currentContent = "# Hello";
    store.currentTitle = "My Page";
    vi.spyOn(store, "hasCurrentPage", "get").mockReturnValue(true);
    return store;
}

describe("PageEditorView", () => {
    beforeEach(() => {
        pinia = createTestingPinia({ createSpy: vi.fn });
        mockConfig.value = { llm_api_configured: true };
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe("Editor view (history mode)", () => {
        let wrapper: Wrapper<Vue>;
        let store: ReturnType<typeof usePageEditorStore>;

        beforeEach(async () => {
            store = setupLoadedPage(HISTORY_ID);
            wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();
        });

        it("shows toolbar and MarkdownEditor when page is loaded", () => {
            expect(wrapper.findComponent(PageDisplayToolbar).exists()).toBe(true);
            expect(wrapper.findComponent(MarkdownEditor).exists()).toBe(true);
        });

        it("passes content to MarkdownEditor", () => {
            const editor = wrapper.findComponent(MarkdownEditor);
            expect(editor.props("markdownText")).toBe("# Hello");
        });

        it("passes page mode to MarkdownEditor when historyId set", () => {
            const editor = wrapper.findComponent(MarkdownEditor);
            expect(editor.props("mode")).toBe("page");
        });

        it("Preview button navigates to displayOnly mode", async () => {
            wrapper.findComponent(PageDisplayToolbar).vm.$emit("preview");

            expect(mockPush).toHaveBeenCalledWith(`/histories/${HISTORY_ID}/pages/${PAGE_ID}?displayOnly=true`);
        });

        it("back button navigates to history pages list", async () => {
            wrapper.findComponent(PageDisplayToolbar).vm.$emit("back");

            expect(store.clearCurrentPage).toHaveBeenCalled();
            expect(mockPush).toHaveBeenCalledWith(`/histories/${HISTORY_ID}/pages`);
        });

        // TODO: We won't have a Save & View but will implement a save changes or ignore modal
        // it("hides save & view button in history mode", () => {
        //     expect(wrapper.find(SELECTORS.SAVE_VIEW_BUTTON).exists()).toBe(false);
        // });
    });

    describe("Editor view (standalone mode)", () => {
        let wrapper: Wrapper<Vue>;

        beforeEach(async () => {
            setupLoadedPage();
            wrapper = mountComponent({ pageId: PAGE_ID });
            await flushPromises();
        });

        it("shows toolbar and MarkdownEditor", () => {
            expect(wrapper.findComponent(PageDisplayToolbar).exists()).toBe(true);
            expect(wrapper.findComponent(MarkdownEditor).exists()).toBe(true);
        });

        it("passes page mode to MarkdownEditor when no historyId", () => {
            const editor = wrapper.findComponent(MarkdownEditor);
            expect(editor.props("mode")).toBe("page");
        });

        // TODO: We won't have a Save & View but will implement a save changes or ignore modal
        // it("shows save & view button in standalone mode", () => {
        //     expect(wrapper.find(SELECTORS.SAVE_VIEW_BUTTON).exists()).toBe(true);
        // });

        it("back button navigates to pages list", async () => {
            wrapper.findComponent(PageDisplayToolbar).vm.$emit("back");
            expect(mockPush).toHaveBeenCalledWith("/pages/list");
        });

        // TODO: We won't have a Save & View but will implement a save changes or ignore modal
        // it("Save & View navigates to published page when WM inactive", async () => {
        //     const store = usePageEditorStore();
        //     store.currentPage = {
        //         id: PAGE_ID,
        //         history_id: null,
        //         title: "My Page",
        //         content: "# Hello",
        //         update_time: "2024-01-01T00:00:00",
        //         username: "testuser",
        //         slug: "my-page",
        //     } as Partial<HistoryPageDetails> as HistoryPageDetails;
        //     store.currentContent = "modified";
        //     store.currentTitle = "My Page";

        //     const saveViewBtn = wrapper.find(SELECTORS.SAVE_VIEW_BUTTON);
        //     // Mock location.href assignment
        //     const hrefSpy = vi.spyOn(window, "location", "get").mockReturnValue({
        //         ...window.location,
        //         href: "",
        //     } as unknown as Location);
        //     await saveViewBtn.trigger("click");
        //     await flushPromises();

        //     expect(store.savePage).toHaveBeenCalled();
        //     hrefSpy.mockRestore();
        // });

        // it("Save & View uses router.push when WM is active", async () => {
        //     mockGalaxyInstance.frame.active = true;
        //     const store = usePageEditorStore();
        //     store.currentPage = {
        //         id: PAGE_ID,
        //         history_id: null,
        //         title: "My Page",
        //         content: "# Hello",
        //         update_time: "2024-01-01T00:00:00",
        //     } as Partial<HistoryPageDetails> as HistoryPageDetails;
        //     store.currentContent = "modified";
        //     store.currentTitle = "My Page";

        //     const saveViewBtn = wrapper.find(SELECTORS.SAVE_VIEW_BUTTON);
        //     await saveViewBtn.trigger("click");
        //     await flushPromises();

        //     expect(store.savePage).toHaveBeenCalled();
        //     expect(mockPush).toHaveBeenCalledWith(
        //         `/published/page?id=${PAGE_ID}&embed=true`,
        //         expect.objectContaining({
        //             title: "Report: My Page",
        //             preventWindowManager: false,
        //         }),
        //     );
        //     mockGalaxyInstance.frame.active = false;
        // });
    });

    describe("DisplayOnly mode", () => {
        it("renders PageDisplayOnly when displayOnly is true", async () => {
            setupLoadedPage(HISTORY_ID);
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID, displayOnly: true });
            await flushPromises();

            expect(wrapper.findComponent(PageDisplayOnly).exists()).toBe(true);
            expect(wrapper.findComponent(PageDisplayToolbar).exists()).toBe(false);
        });

        it("does not clear editor state on unmount in displayOnly mode", async () => {
            setupLoadedPage(HISTORY_ID);
            const store = usePageEditorStore();
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID, displayOnly: true });
            await flushPromises();

            wrapper.destroy();
            expect(store.$reset).not.toHaveBeenCalled();
            expect(store.clearCurrentPage).not.toHaveBeenCalled();
        });
    });

    describe("Revision UI", () => {
        it("shows revision list in a modal when store.showRevisions is true", async () => {
            const store = setupLoadedPage(HISTORY_ID);
            store.showRevisions = true;
            store.revisions = [] as PageRevisionSummary[];
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            expect(wrapper.findComponent(GModal).props("show")).toBe(true);
        });

        it("hides revision modal when store.showRevisions is false", async () => {
            setupLoadedPage(HISTORY_ID);
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            expect(wrapper.findComponent(GModal).props("show")).toBe(false);
        });

        it("shows PageRevisionView when selectedRevision is set", async () => {
            const store = setupLoadedPage(HISTORY_ID);
            store.selectedRevision = {
                id: "rev-1",
                page_id: PAGE_ID,
                content: "# Old content",
                content_format: "markdown",
                edit_source: "user",
                create_time: "2024-01-01T00:00:00",
                update_time: "2024-01-01T00:00:00",
            } as PageRevisionDetails;
            store.previousRevisionContent = "";
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            expect(wrapper.findComponent(PageRevisionView).exists()).toBe(true);
            expect(wrapper.findComponent(MarkdownEditor).exists()).toBe(false);
        });

        it("PageRevisionView back emits clearSelectedRevision", async () => {
            const store = setupLoadedPage(HISTORY_ID);
            store.selectedRevision = {
                id: "rev-1",
                page_id: PAGE_ID,
                content: "# Old",
                content_format: "markdown",
                edit_source: "user",
                create_time: "2024-01-01T00:00:00",
                update_time: "2024-01-01T00:00:00",
            } as PageRevisionDetails;
            store.previousRevisionContent = "";
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            const revView = wrapper.findComponent(PageRevisionView);
            revView.vm.$emit("back");
            await wrapper.vm.$nextTick();

            expect(store.clearSelectedRevision).toHaveBeenCalled();
        });

        it("PageRevisionView restore calls store.restoreRevision", async () => {
            const store = setupLoadedPage(HISTORY_ID);
            store.selectedRevision = {
                id: "rev-1",
                page_id: PAGE_ID,
                content: "# Old",
                content_format: "markdown",
                edit_source: "user",
                create_time: "2024-01-01T00:00:00",
                update_time: "2024-01-01T00:00:00",
            } as PageRevisionDetails;
            store.previousRevisionContent = "";
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            const revView = wrapper.findComponent(PageRevisionView);
            revView.vm.$emit("restore", "rev-1");
            await wrapper.vm.$nextTick();

            expect(store.restoreRevision).toHaveBeenCalledWith("rev-1");
        });

        it("revision list select calls store.loadRevision", async () => {
            const store = setupLoadedPage(HISTORY_ID);
            store.showRevisions = true;
            store.revisions = [
                { id: "rev-1", page_id: PAGE_ID, edit_source: "user", create_time: "", update_time: "" },
            ] as PageRevisionSummary[];
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            const revList = wrapper.findComponent(PageRevisionList);
            revList.vm.$emit("select", "rev-1");
            await wrapper.vm.$nextTick();

            expect(store.loadRevision).toHaveBeenCalledWith("rev-1");
        });
    });

    describe("Revision UI (standalone mode)", () => {
        it("revision list restore calls store.restoreRevision in standalone mode", async () => {
            const store = setupLoadedPage();
            store.showRevisions = true;
            store.revisions = [
                { id: "rev-1", page_id: PAGE_ID, edit_source: "user", create_time: "", update_time: "" },
            ] as PageRevisionSummary[];
            const wrapper = mountComponent({ pageId: PAGE_ID });
            await flushPromises();

            const revList = wrapper.findComponent(PageRevisionList);
            revList.vm.$emit("restore", "rev-1");
            await wrapper.vm.$nextTick();

            expect(store.restoreRevision).toHaveBeenCalledWith("rev-1");
        });
    });

    describe("Lifecycle", () => {
        it("calls store.loadPage on mount", async () => {
            const store = usePageEditorStore();
            mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            expect(store.loadPage).toHaveBeenCalledWith(PAGE_ID);
        });

        it("sets store mode to history when historyId provided", async () => {
            const store = usePageEditorStore();
            mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            expect(store.mode).toBe("history");
        });

        it("sets store mode to standalone when no historyId", async () => {
            const store = usePageEditorStore();
            mountComponent({ pageId: PAGE_ID });
            await flushPromises();

            expect(store.mode).toBe("standalone");
        });

        it("calls store.clearCurrentPage (not $reset) on unmount so store.error survives", async () => {
            const store = usePageEditorStore();
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            wrapper.destroy();
            expect(store.clearCurrentPage).toHaveBeenCalled();
            expect(store.$reset).not.toHaveBeenCalled();
        });

        it("does not clear store.error on unmount in edit mode", async () => {
            setupLoadedPage(HISTORY_ID);
            const store = usePageEditorStore();
            store.error = "Save failed";
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            wrapper.destroy();
            expect(store.error).toBe("Save failed");
        });
    });

    describe("Error alert", () => {
        it("renders error alert alongside the editor (not in place of it)", async () => {
            const store = setupLoadedPage(HISTORY_ID);
            store.error = "Save failed";
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            const errorAlert = wrapper.find("balert-stub[variant='danger']");
            expect(errorAlert.exists()).toBe(true);
            expect(errorAlert.text()).toContain("Save failed");
            expect(wrapper.findComponent(PageDisplayToolbar).exists()).toBe(true);
            expect(wrapper.findComponent(MarkdownEditor).exists()).toBe(true);
        });
    });
});
