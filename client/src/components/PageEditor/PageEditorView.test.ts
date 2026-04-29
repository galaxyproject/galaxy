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

import EditorSplitView from "./EditorSplitView.vue";
import PageChatPanel from "./PageChatPanel.vue";
import PageEditorView from "./PageEditorView.vue";
import PageRevisionList from "./PageRevisionList.vue";
import PageRevisionView from "./PageRevisionView.vue";
import ClickToEdit from "@/components/ClickToEdit.vue";
import Markdown from "@/components/Markdown/Markdown.vue";
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

const mockGalaxyInstance = { frame: { active: false } };
vi.mock("@/app", () => ({
    getGalaxyInstance: vi.fn(() => mockGalaxyInstance),
}));

const localVue = getLocalVue();

const HISTORY_ID = "history-1";
const PAGE_ID = "page-1";

const SELECTORS = {
    TOOLBAR: "[data-description='page editor toolbar']",
    TOOLBAR_TITLE: "[data-description='page editor title']",
    SAVE_BUTTON: "[data-description='page save button']",
    BACK_BUTTON: "[data-description='page back button']",
    UNSAVED_INDICATOR: "[data-description='page unsaved indicator']",
    REVISIONS_BUTTON: "[data-description='page revisions button']",
    REVISION_PANEL: ".page-revision-panel",
    CHAT_BUTTON: "[data-description='page chat button']",
    PREVIEW_BUTTON: "[data-description='page preview button']",
    PERMISSIONS_BUTTON: "[data-description='page permissions button']",
    SAVE_VIEW_BUTTON: "[data-description='page save-view button']",
    EDIT_BUTTON: "[data-description='page edit button']",
    DISPLAY_TOOLBAR: "[data-description='page display toolbar']",
};

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
    } as Partial<HistoryPageDetails> as HistoryPageDetails;
    store.currentContent = "# Hello";
    store.currentTitle = "My Page";
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
            expect(wrapper.find(SELECTORS.TOOLBAR).exists()).toBe(true);
            expect(wrapper.findComponent(MarkdownEditor).exists()).toBe(true);
        });

        it("shows ClickToEdit with page title in toolbar", () => {
            const clickToEdit = wrapper.findComponent(ClickToEdit);
            expect(clickToEdit.exists()).toBe(true);
            expect(clickToEdit.props("value")).toBe("My Page");
        });

        it("shows 'Untitled Notebook' in ClickToEdit when currentTitle is empty", async () => {
            store.currentTitle = "";
            await wrapper.vm.$nextTick();

            const clickToEdit = wrapper.findComponent(ClickToEdit);
            expect(clickToEdit.props("value")).toBe("Untitled Notebook");
        });

        it("shows 'Unsaved' indicator when store.isDirty is true", async () => {
            await wrapper.vm.$nextTick();

            expect(store.isDirty).toBe(true);
            const unsaved = wrapper.find(SELECTORS.UNSAVED_INDICATOR);
            expect(unsaved.exists()).toBe(true);
            expect(unsaved.text()).toBe("Unsaved");
        });

        it("save button is disabled when store.canSave is false", async () => {
            store.currentContent = "";
            store.currentTitle = "";
            await wrapper.vm.$nextTick();

            expect(store.canSave).toBe(false);
            const saveBtn = wrapper.find(SELECTORS.SAVE_BUTTON);
            expect(saveBtn.attributes("disabled")).toBe("true");
        });

        it("passes content to MarkdownEditor", () => {
            const editor = wrapper.findComponent(MarkdownEditor);
            expect(editor.props("markdownText")).toBe("# Hello");
        });

        it("passes page mode to MarkdownEditor when historyId set", () => {
            const editor = wrapper.findComponent(MarkdownEditor);
            expect(editor.props("mode")).toBe("page");
        });

        it("shows Preview button in toolbar", () => {
            const previewBtn = wrapper.find(SELECTORS.PREVIEW_BUTTON);
            expect(previewBtn.exists()).toBe(true);
            expect(previewBtn.text()).toContain("Preview");
        });

        it("Preview button navigates to displayOnly mode", async () => {
            const previewBtn = wrapper.find(SELECTORS.PREVIEW_BUTTON);
            await previewBtn.trigger("click");

            expect(mockPush).toHaveBeenCalledWith(`/histories/${HISTORY_ID}/pages/${PAGE_ID}?displayOnly=true`);
        });

        it("ClickToEdit input updates store title", async () => {
            const clickToEdit = wrapper.findComponent(ClickToEdit);
            clickToEdit.vm.$emit("input", "Renamed Page");
            await wrapper.vm.$nextTick();

            expect(store.updateTitle).toHaveBeenCalledWith("Renamed Page");
        });

        it("back button navigates to history pages list", async () => {
            const backBtn = wrapper.find(SELECTORS.BACK_BUTTON);
            await backBtn.trigger("click");

            expect(store.clearCurrentPage).toHaveBeenCalled();
            expect(mockPush).toHaveBeenCalledWith(`/histories/${HISTORY_ID}/pages`);
        });

        it("save button calls store.savePage", async () => {
            const saveBtn = wrapper.find(SELECTORS.SAVE_BUTTON);
            await saveBtn.trigger("click");
            await flushPromises();

            expect(store.savePage).toHaveBeenCalled();
        });

        it("hides permissions button in history mode", () => {
            expect(wrapper.find(SELECTORS.PERMISSIONS_BUTTON).exists()).toBe(false);
        });

        it("hides save & view button in history mode", () => {
            expect(wrapper.find(SELECTORS.SAVE_VIEW_BUTTON).exists()).toBe(false);
        });
    });

    describe("Editor view (standalone mode)", () => {
        let wrapper: Wrapper<Vue>;

        beforeEach(async () => {
            setupLoadedPage();
            wrapper = mountComponent({ pageId: PAGE_ID });
            await flushPromises();
        });

        it("shows toolbar and MarkdownEditor", () => {
            expect(wrapper.find(SELECTORS.TOOLBAR).exists()).toBe(true);
            expect(wrapper.findComponent(MarkdownEditor).exists()).toBe(true);
        });

        it("passes page mode to MarkdownEditor when no historyId", () => {
            const editor = wrapper.findComponent(MarkdownEditor);
            expect(editor.props("mode")).toBe("page");
        });

        it("shows permissions button in standalone mode", () => {
            expect(wrapper.find(SELECTORS.PERMISSIONS_BUTTON).exists()).toBe(true);
        });

        it("shows save & view button in standalone mode", () => {
            expect(wrapper.find(SELECTORS.SAVE_VIEW_BUTTON).exists()).toBe(true);
        });

        it("back button navigates to pages list", async () => {
            const backBtn = wrapper.find(SELECTORS.BACK_BUTTON);
            await backBtn.trigger("click");

            expect(mockPush).toHaveBeenCalledWith("/pages/list");
        });

        it("back button text says 'Back to Reports'", () => {
            const backBtn = wrapper.find(SELECTORS.BACK_BUTTON);
            expect(backBtn.text()).toContain("Back to Reports");
        });

        it("Save & View navigates to published page when WM inactive", async () => {
            const store = usePageEditorStore();
            store.currentPage = {
                id: PAGE_ID,
                history_id: null,
                title: "My Page",
                content: "# Hello",
                update_time: "2024-01-01T00:00:00",
                username: "testuser",
                slug: "my-page",
            } as Partial<HistoryPageDetails> as HistoryPageDetails;
            store.currentContent = "modified";
            store.currentTitle = "My Page";

            const saveViewBtn = wrapper.find(SELECTORS.SAVE_VIEW_BUTTON);
            // Mock location.href assignment
            const hrefSpy = vi.spyOn(window, "location", "get").mockReturnValue({
                ...window.location,
                href: "",
            } as unknown as Location);
            await saveViewBtn.trigger("click");
            await flushPromises();

            expect(store.savePage).toHaveBeenCalled();
            hrefSpy.mockRestore();
        });

        it("Save & View uses router.push when WM is active", async () => {
            mockGalaxyInstance.frame.active = true;
            const store = usePageEditorStore();
            store.currentPage = {
                id: PAGE_ID,
                history_id: null,
                title: "My Page",
                content: "# Hello",
                update_time: "2024-01-01T00:00:00",
            } as Partial<HistoryPageDetails> as HistoryPageDetails;
            store.currentContent = "modified";
            store.currentTitle = "My Page";

            const saveViewBtn = wrapper.find(SELECTORS.SAVE_VIEW_BUTTON);
            await saveViewBtn.trigger("click");
            await flushPromises();

            expect(store.savePage).toHaveBeenCalled();
            expect(mockPush).toHaveBeenCalledWith(
                `/published/page?id=${PAGE_ID}&embed=true`,
                expect.objectContaining({
                    title: "Report: My Page",
                    preventWindowManager: false,
                }),
            );
            mockGalaxyInstance.frame.active = false;
        });
    });

    describe("DisplayOnly mode", () => {
        it("renders Markdown when displayOnly is true", async () => {
            setupLoadedPage(HISTORY_ID);
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID, displayOnly: true });
            await flushPromises();

            expect(wrapper.findComponent(Markdown).exists()).toBe(true);
            expect(wrapper.find(SELECTORS.TOOLBAR).exists()).toBe(false);
        });

        it("shows display toolbar with Edit button", async () => {
            setupLoadedPage(HISTORY_ID);
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID, displayOnly: true });
            await flushPromises();

            expect(wrapper.find(SELECTORS.DISPLAY_TOOLBAR).exists()).toBe(true);
            const editBtn = wrapper.find(SELECTORS.EDIT_BUTTON);
            expect(editBtn.exists()).toBe(true);
        });

        it("does not call store.$reset on unmount in displayOnly mode", async () => {
            setupLoadedPage(HISTORY_ID);
            const store = usePageEditorStore();
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID, displayOnly: true });
            await flushPromises();

            wrapper.destroy();
            expect(store.$reset).not.toHaveBeenCalled();
        });
    });

    describe("Revision UI", () => {
        it("shows Revisions button in toolbar", async () => {
            setupLoadedPage(HISTORY_ID);
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            const revBtn = wrapper.find(SELECTORS.REVISIONS_BUTTON);
            expect(revBtn.exists()).toBe(true);
            expect(revBtn.text()).toContain("Revisions");
        });

        it("clicking Revisions button calls store.toggleRevisions", async () => {
            const store = setupLoadedPage(HISTORY_ID);
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            const revBtn = wrapper.find(SELECTORS.REVISIONS_BUTTON);
            await revBtn.trigger("click");

            expect(store.toggleRevisions).toHaveBeenCalled();
        });

        it("shows revision panel when store.showRevisions is true", async () => {
            const store = setupLoadedPage(HISTORY_ID);
            store.showRevisions = true;
            store.revisions = [] as PageRevisionSummary[];
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            expect(wrapper.find(SELECTORS.REVISION_PANEL).exists()).toBe(true);
            expect(wrapper.findComponent(PageRevisionList).exists()).toBe(true);
        });

        it("hides revision panel when store.showRevisions is false", async () => {
            setupLoadedPage(HISTORY_ID);
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            expect(wrapper.find(SELECTORS.REVISION_PANEL).exists()).toBe(false);
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
            expect(wrapper.find(SELECTORS.TOOLBAR).exists()).toBe(false);
        });

        it("revision badge shows count when revisions loaded", async () => {
            const store = setupLoadedPage(HISTORY_ID);
            store.revisions = [
                { id: "rev-1", page_id: PAGE_ID, edit_source: "user", create_time: "", update_time: "" },
                { id: "rev-2", page_id: PAGE_ID, edit_source: "user", create_time: "", update_time: "" },
            ] as PageRevisionSummary[];
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            const badge = wrapper.find(SELECTORS.REVISIONS_BUTTON + " bbadge-stub");
            expect(badge.exists()).toBe(true);
            expect(badge.text()).toBe("2");
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

        it("revision panel select calls store.loadRevision", async () => {
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
        it("shows Revisions button in standalone mode", async () => {
            setupLoadedPage();
            const wrapper = mountComponent({ pageId: PAGE_ID });
            await flushPromises();

            const revBtn = wrapper.find(SELECTORS.REVISIONS_BUTTON);
            expect(revBtn.exists()).toBe(true);
            expect(revBtn.text()).toContain("Revisions");
        });

        it("clicking Revisions button calls store.toggleRevisions in standalone mode", async () => {
            const store = setupLoadedPage();
            const wrapper = mountComponent({ pageId: PAGE_ID });
            await flushPromises();

            const revBtn = wrapper.find(SELECTORS.REVISIONS_BUTTON);
            await revBtn.trigger("click");

            expect(store.toggleRevisions).toHaveBeenCalled();
        });

        it("shows revision panel when store.showRevisions is true in standalone mode", async () => {
            const store = setupLoadedPage();
            store.showRevisions = true;
            store.revisions = [
                { id: "rev-1", page_id: PAGE_ID, edit_source: "user", create_time: "", update_time: "" },
            ] as PageRevisionSummary[];
            const wrapper = mountComponent({ pageId: PAGE_ID });
            await flushPromises();

            expect(wrapper.find(SELECTORS.REVISION_PANEL).exists()).toBe(true);
            expect(wrapper.findComponent(PageRevisionList).exists()).toBe(true);
        });

        it("revision panel restore calls store.restoreRevision in standalone mode", async () => {
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

    describe("Chat Panel", () => {
        it("shows Chat button in toolbar", async () => {
            setupLoadedPage(HISTORY_ID);
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            const chatBtn = wrapper.find(SELECTORS.CHAT_BUTTON);
            expect(chatBtn.exists()).toBe(true);
            expect(chatBtn.text()).toContain("Chat");
        });

        it("clicking Chat button calls store.toggleChatPanel", async () => {
            const store = setupLoadedPage(HISTORY_ID);
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            const chatBtn = wrapper.find(SELECTORS.CHAT_BUTTON);
            await chatBtn.trigger("click");
            await flushPromises();

            expect(store.toggleChatPanel).toHaveBeenCalled();
        });

        it("renders split view when store.showChatPanel is true", async () => {
            const store = setupLoadedPage(HISTORY_ID);
            store.showChatPanel = true;
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            expect(wrapper.findComponent(EditorSplitView).exists()).toBe(true);
            expect(wrapper.findComponent(PageChatPanel).exists()).toBe(true);
        });

        it("hides split view when store.showChatPanel is false", async () => {
            const store = setupLoadedPage(HISTORY_ID);
            store.showChatPanel = false;
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            expect(wrapper.findComponent(EditorSplitView).exists()).toBe(false);
        });

        it("hides Chat button when llm_api_configured is false", async () => {
            setupLoadedPage(HISTORY_ID);
            mockConfig.value = { llm_api_configured: false };
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            expect(wrapper.find(SELECTORS.CHAT_BUTTON).exists()).toBe(false);
        });

        it("shows Chat button when llm_api_configured is true", async () => {
            setupLoadedPage(HISTORY_ID);
            mockConfig.value = { llm_api_configured: true };
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            expect(wrapper.find(SELECTORS.CHAT_BUTTON).exists()).toBe(true);
        });

        it("hides Chat button when config is null (not yet loaded)", async () => {
            setupLoadedPage(HISTORY_ID);
            mockConfig.value = null;
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            expect(wrapper.find(SELECTORS.CHAT_BUTTON).exists()).toBe(false);
        });

        it("passes props to PageChatPanel", async () => {
            const store = setupLoadedPage(HISTORY_ID);
            store.showChatPanel = true;
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            const panel = wrapper.findComponent(PageChatPanel);
            expect(panel.props("historyId")).toBe(HISTORY_ID);
            expect(panel.props("pageId")).toBe(PAGE_ID);
            expect(panel.props("pageContent")).toBe("# Hello");
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

        it("calls store.$reset on unmount", async () => {
            const store = usePageEditorStore();
            const wrapper = mountComponent({ pageId: PAGE_ID, historyId: HISTORY_ID });
            await flushPromises();

            wrapper.destroy();
            expect(store.$reset).toHaveBeenCalled();
        });
    });
});
