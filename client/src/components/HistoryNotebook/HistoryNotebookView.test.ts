import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import type { Pinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { usePageEditorStore } from "@/stores/pageEditorStore";

import HistoryNotebookEditor from "./HistoryNotebookEditor.vue";
import HistoryNotebookList from "./HistoryNotebookList.vue";
import HistoryNotebookSplit from "./HistoryNotebookSplit.vue";
import HistoryNotebookView from "./HistoryNotebookView.vue";
import NotebookChatPanel from "./NotebookChatPanel.vue";
import NotebookRevisionList from "./NotebookRevisionList.vue";
import NotebookRevisionView from "./NotebookRevisionView.vue";
import ClickToEdit from "@/components/ClickToEdit.vue";
import Markdown from "@/components/Markdown/Markdown.vue";

const mockConfig = ref<any>({ llm_api_configured: true });

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
    INFO_ALERT: "balert-stub[variant='info']",
    ERROR_ALERT: "balert-stub[variant='danger']",
    TOOLBAR: ".notebook-toolbar",
    TOOLBAR_TITLE: ".notebook-toolbar .flex-grow-1",
    SAVE_BUTTON: ".notebook-toolbar bbutton-stub[variant='primary']",
    MANAGE_BUTTON: ".notebook-toolbar bbutton-stub[variant='link']",
    UNSAVED_INDICATOR: ".notebook-toolbar .text-warning",
    REVISIONS_BUTTON: "[data-description='notebook revisions button']",
    REVISION_PANEL: ".notebook-revision-panel",
    CHAT_BUTTON: "[data-description='notebook chat button']",
    PREVIEW_BUTTON: "[data-description='notebook preview button']",
    EDIT_BUTTON: "[data-description='notebook edit button']",
    DISPLAY_TOOLBAR: "[data-description='notebook display toolbar']",
};

let pinia: Pinia;

function mountComponent(propsData: { historyId: string; pageId?: string; displayOnly?: boolean }) {
    return shallowMount(HistoryNotebookView as object, {
        localVue,
        propsData,
        pinia,
    });
}

function setupListViewStore(notebooks: any[] = []) {
    const store = usePageEditorStore();
    store.isLoadingList = false;
    store.error = null;
    store.notebooks = notebooks as any;
    return store;
}

describe("HistoryNotebookView", () => {
    beforeEach(() => {
        pinia = createTestingPinia({ createSpy: vi.fn });
        mockConfig.value = { llm_api_configured: true };
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe("Loading state", () => {
        it("shows loading alert when isLoadingList is true", async () => {
            const store = usePageEditorStore();
            store.isLoadingList = true;
            const wrapper = mountComponent({ historyId: HISTORY_ID });
            await flushPromises();

            const alerts = wrapper.findAll(SELECTORS.INFO_ALERT);
            const loadingAlert = alerts.wrappers.find((w) => w.text().includes("Loading pages"));
            expect(loadingAlert).toBeTruthy();
        });

        it("shows loading alert when isLoadingNotebook is true and notebookId provided", async () => {
            const store = usePageEditorStore();
            store.isLoadingList = false;
            store.isLoadingNotebook = true;
            // hasCurrentNotebook is a computed - set currentNotebook to null so
            // hasCurrentNotebook evaluates to false, falling through to the loading check
            store.currentNotebook = null;
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            const alerts = wrapper.findAll(SELECTORS.INFO_ALERT);
            const loadingAlert = alerts.wrappers.find((w) => w.text().includes("Loading page"));
            expect(loadingAlert).toBeTruthy();
        });
    });

    describe("Error state", () => {
        it("shows error alert when store.error is set", async () => {
            const store = usePageEditorStore();
            store.isLoadingList = false;
            store.error = "Something went wrong";
            const wrapper = mountComponent({ historyId: HISTORY_ID });
            await flushPromises();

            const errorAlert = wrapper.find(SELECTORS.ERROR_ALERT);
            expect(errorAlert.exists()).toBe(true);
            expect(errorAlert.text()).toContain("Something went wrong");
        });
    });

    describe("List view (no notebookId)", () => {
        it("shows HistoryNotebookList when no notebookId and not loading/error", async () => {
            setupListViewStore();
            const wrapper = mountComponent({ historyId: HISTORY_ID });
            await flushPromises();

            expect(wrapper.findComponent(HistoryNotebookList).exists()).toBe(true);
        });

        it("passes store.notebooks to HistoryNotebookList", async () => {
            const fakeNotebooks = [
                { id: "nb-1", history_id: HISTORY_ID, title: "NB1", deleted: false, create_time: "", update_time: "" },
            ];
            setupListViewStore(fakeNotebooks);
            const wrapper = mountComponent({ historyId: HISTORY_ID });
            await flushPromises();

            const list = wrapper.findComponent(HistoryNotebookList);
            expect(list.props("notebooks")).toEqual(fakeNotebooks);
        });
    });

    describe("Editor view (with notebookId and current notebook loaded)", () => {
        let wrapper: Wrapper<Vue>;
        let store: ReturnType<typeof usePageEditorStore>;

        beforeEach(async () => {
            store = usePageEditorStore();
            store.isLoadingList = false;
            store.isLoadingNotebook = false;
            store.error = null;
            store.currentNotebook = {
                id: PAGE_ID,
                history_id: HISTORY_ID,
                title: "My Notebook",
                content: "# Hello",
            } as any;
            store.currentContent = "# Hello";
            store.currentTitle = "My Notebook";
            wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();
        });

        it("shows toolbar and HistoryNotebookEditor when notebook is loaded", () => {
            expect(wrapper.find(SELECTORS.TOOLBAR).exists()).toBe(true);
            expect(wrapper.findComponent(HistoryNotebookEditor).exists()).toBe(true);
        });

        it("shows ClickToEdit with notebook title in toolbar", () => {
            const clickToEdit = wrapper.findComponent(ClickToEdit);
            expect(clickToEdit.exists()).toBe(true);
            expect(clickToEdit.props("value")).toBe("My Notebook");
        });

        it("shows 'Untitled Notebook' in ClickToEdit when currentTitle is empty", async () => {
            store.currentTitle = "";
            await wrapper.vm.$nextTick();

            const clickToEdit = wrapper.findComponent(ClickToEdit);
            expect(clickToEdit.props("value")).toBe("Untitled Page");
        });

        it("shows 'Unsaved' indicator when store.isDirty is true", async () => {
            // isDirty is computed: currentContent !== originalContent.
            // In testing pinia, originalContent defaults to "" while beforeEach sets
            // currentContent to "# Hello", so isDirty is already true.
            await wrapper.vm.$nextTick();

            expect(store.isDirty).toBe(true);
            const unsaved = wrapper.find(SELECTORS.UNSAVED_INDICATOR);
            expect(unsaved.exists()).toBe(true);
            expect(unsaved.text()).toBe("Unsaved");
        });

        it("save button is disabled when store.canSave is false", async () => {
            // isDirty checks both content and title against originals.
            // Set both to match so isDirty=false, canSave=false.
            store.currentContent = "";
            store.currentTitle = "";
            await wrapper.vm.$nextTick();

            expect(store.canSave).toBe(false);
            const saveBtn = wrapper.find(SELECTORS.SAVE_BUTTON);
            expect(saveBtn.attributes("disabled")).toBe("true");
        });

        it("passes content to HistoryNotebookEditor", () => {
            const editor = wrapper.findComponent(HistoryNotebookEditor);
            expect(editor.props("content")).toBe("# Hello");
        });

        it("passes historyId to HistoryNotebookEditor", () => {
            const editor = wrapper.findComponent(HistoryNotebookEditor);
            expect(editor.props("historyId")).toBe(HISTORY_ID);
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
            clickToEdit.vm.$emit("input", "Renamed Notebook");
            await wrapper.vm.$nextTick();

            expect(store.updateTitle).toHaveBeenCalledWith("Renamed Notebook");
        });
    });

    describe("Navigation/Events", () => {
        it("handleSelect navigates to notebook URL via router.push", async () => {
            setupListViewStore([{ id: "nb-1", history_id: HISTORY_ID, title: "NB1" }]);
            const wrapper = mountComponent({ historyId: HISTORY_ID });
            await flushPromises();

            const list = wrapper.findComponent(HistoryNotebookList);
            list.vm.$emit("select", "nb-1");
            await wrapper.vm.$nextTick();

            expect(mockPush).toHaveBeenCalledWith(`/histories/${HISTORY_ID}/pages/nb-1`);
        });

        it("handleCreate calls store.createNotebook and navigates on success", async () => {
            const store = setupListViewStore();
            vi.mocked(store.createNotebook).mockResolvedValue({
                id: "new-notebook",
                history_id: HISTORY_ID,
                title: "Untitled Page",
                content: "",
            } as any);
            const wrapper = mountComponent({ historyId: HISTORY_ID });
            await flushPromises();

            const list = wrapper.findComponent(HistoryNotebookList);
            list.vm.$emit("create");
            await flushPromises();

            expect(store.createNotebook).toHaveBeenCalledWith({ title: "Untitled Page" });
            expect(mockPush).toHaveBeenCalledWith(`/histories/${HISTORY_ID}/pages/new-notebook`);
        });

        it("Manage History Notebooks calls clearCurrentNotebook and navigates to list", async () => {
            const store = setupListViewStore();
            store.isLoadingNotebook = false;
            store.currentNotebook = { id: PAGE_ID, history_id: HISTORY_ID, title: "NB", content: "" } as any;
            store.currentTitle = "NB";
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            const manageBtn = wrapper.find(SELECTORS.MANAGE_BUTTON);
            await manageBtn.trigger("click");

            expect(store.clearCurrentNotebook).toHaveBeenCalled();
            expect(mockPush).toHaveBeenCalledWith(`/histories/${HISTORY_ID}/pages`);
        });

        it("view emit from list navigates to displayOnly URL", async () => {
            setupListViewStore([{ id: "nb-1", history_id: HISTORY_ID, title: "NB1" }]);
            const wrapper = mountComponent({ historyId: HISTORY_ID });
            await flushPromises();

            const list = wrapper.findComponent(HistoryNotebookList);
            list.vm.$emit("view", "nb-1");
            await wrapper.vm.$nextTick();

            expect(mockPush).toHaveBeenCalledWith(`/histories/${HISTORY_ID}/pages/nb-1?displayOnly=true`);
        });

        it("handleSave calls store.saveNotebook", async () => {
            const store = setupListViewStore();
            store.isLoadingNotebook = false;
            store.currentNotebook = { id: PAGE_ID, history_id: HISTORY_ID, title: "NB", content: "" } as any;
            store.currentTitle = "NB";
            // canSave is true because currentContent differs from originalContent (defaults to "")
            store.currentContent = "# Modified";
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            expect(store.canSave).toBe(true);
            const saveBtn = wrapper.find(SELECTORS.SAVE_BUTTON);
            await saveBtn.trigger("click");
            await flushPromises();

            expect(store.saveNotebook).toHaveBeenCalled();
        });
    });

    describe("DisplayOnly mode", () => {
        function setupLoadedNotebook() {
            const store = usePageEditorStore();
            store.isLoadingList = false;
            store.isLoadingNotebook = false;
            store.error = null;
            store.currentNotebook = {
                id: PAGE_ID,
                history_id: HISTORY_ID,
                title: "My Notebook",
                content: "# Hello",
                update_time: "2024-01-01T00:00:00",
            } as any;
            store.currentContent = "# Hello";
            store.currentTitle = "My Notebook";
            return store;
        }

        it("renders editor when displayOnly is false", async () => {
            setupLoadedNotebook();
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID, displayOnly: false });
            await flushPromises();

            expect(wrapper.find(SELECTORS.TOOLBAR).exists()).toBe(true);
            expect(wrapper.findComponent(HistoryNotebookEditor).exists()).toBe(true);
            expect(wrapper.findComponent(Markdown).exists()).toBe(false);
        });

        it("renders Markdown when displayOnly is true", async () => {
            setupLoadedNotebook();
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID, displayOnly: true });
            await flushPromises();

            expect(wrapper.findComponent(Markdown).exists()).toBe(true);
            expect(wrapper.find(SELECTORS.TOOLBAR).exists()).toBe(false);
            expect(wrapper.findComponent(HistoryNotebookEditor).exists()).toBe(false);
        });

        it("passes correct markdownConfig to Markdown", async () => {
            setupLoadedNotebook();
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID, displayOnly: true });
            await flushPromises();

            const md = wrapper.findComponent(Markdown);
            const config = md.props("markdownConfig");
            expect(config.id).toBe(PAGE_ID);
            expect(config.title).toBe("My Notebook");
            expect(config.content).toBe("# Hello");
        });

        it("shows display toolbar with Edit button", async () => {
            setupLoadedNotebook();
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID, displayOnly: true });
            await flushPromises();

            expect(wrapper.find(SELECTORS.DISPLAY_TOOLBAR).exists()).toBe(true);
            const editBtn = wrapper.find(SELECTORS.EDIT_BUTTON);
            expect(editBtn.exists()).toBe(true);
            expect(editBtn.text()).toContain("Edit");
        });

        it("Edit button navigates to edit mode (no displayOnly)", async () => {
            setupLoadedNotebook();
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID, displayOnly: true });
            await flushPromises();

            const editBtn = wrapper.find(SELECTORS.EDIT_BUTTON);
            await editBtn.trigger("click");

            expect(mockPush).toHaveBeenCalledWith(`/histories/${HISTORY_ID}/pages/${PAGE_ID}`);
        });

        it("list view renders normally regardless of displayOnly", async () => {
            setupListViewStore();
            const wrapper = mountComponent({ historyId: HISTORY_ID, displayOnly: true });
            await flushPromises();

            expect(wrapper.findComponent(HistoryNotebookList).exists()).toBe(true);
        });

        it("does not call store.$reset on unmount in displayOnly mode", async () => {
            setupLoadedNotebook();
            const store = usePageEditorStore();
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID, displayOnly: true });
            await flushPromises();

            wrapper.destroy();
            expect(store.$reset).not.toHaveBeenCalled();
        });
    });

    describe("Window Manager integration", () => {
        afterEach(() => {
            mockGalaxyInstance.frame.active = false;
        });

        it("handleSelect opens in WinBox when WM is active", async () => {
            mockGalaxyInstance.frame.active = true;
            setupListViewStore([{ id: "nb-1", history_id: HISTORY_ID, title: "NB1" }]);
            const wrapper = mountComponent({ historyId: HISTORY_ID });
            await flushPromises();

            const list = wrapper.findComponent(HistoryNotebookList);
            list.vm.$emit("select", "nb-1");
            await wrapper.vm.$nextTick();

            expect(mockPush).toHaveBeenCalledWith(`/histories/${HISTORY_ID}/pages/nb-1?displayOnly=true`, {
                title: "Page: NB1",
                preventWindowManager: false,
            });
        });
    });

    describe("Lifecycle", () => {
        it("calls store.loadNotebooks on mount", async () => {
            const store = usePageEditorStore();
            mountComponent({ historyId: HISTORY_ID });
            await flushPromises();

            expect(store.loadNotebooks).toHaveBeenCalledWith(HISTORY_ID);
        });

        it("calls store.loadNotebook on mount if notebookId provided", async () => {
            const store = usePageEditorStore();
            mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            expect(store.loadNotebook).toHaveBeenCalledWith(PAGE_ID);
        });

        it("does not call store.loadNotebook on mount when no notebookId", async () => {
            const store = usePageEditorStore();
            mountComponent({ historyId: HISTORY_ID });
            await flushPromises();

            expect(store.loadNotebook).not.toHaveBeenCalled();
        });

        it("calls store.$reset on unmount", async () => {
            const store = usePageEditorStore();
            const wrapper = mountComponent({ historyId: HISTORY_ID });
            await flushPromises();

            wrapper.destroy();
            expect(store.$reset).toHaveBeenCalled();
        });
    });

    describe("Revision UI", () => {
        function setupEditorView() {
            const store = usePageEditorStore();
            store.isLoadingList = false;
            store.isLoadingNotebook = false;
            store.error = null;
            store.currentNotebook = {
                id: PAGE_ID,
                history_id: HISTORY_ID,
                title: "My Notebook",
                content: "# Hello",
                update_time: "2024-01-01T00:00:00",
            } as any;
            store.currentContent = "# Hello";
            store.currentTitle = "My Notebook";
            return store;
        }

        it("shows Revisions button in toolbar", async () => {
            setupEditorView();
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            const revBtn = wrapper.find(SELECTORS.REVISIONS_BUTTON);
            expect(revBtn.exists()).toBe(true);
            expect(revBtn.text()).toContain("Revisions");
        });

        it("clicking Revisions button calls store.toggleRevisions", async () => {
            const store = setupEditorView();
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            const revBtn = wrapper.find(SELECTORS.REVISIONS_BUTTON);
            await revBtn.trigger("click");

            expect(store.toggleRevisions).toHaveBeenCalled();
        });

        it("shows revision panel when store.showRevisions is true", async () => {
            const store = setupEditorView();
            store.showRevisions = true;
            store.revisions = [] as any;
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            expect(wrapper.find(SELECTORS.REVISION_PANEL).exists()).toBe(true);
            expect(wrapper.findComponent(NotebookRevisionList).exists()).toBe(true);
        });

        it("hides revision panel when store.showRevisions is false", async () => {
            setupEditorView();
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            expect(wrapper.find(SELECTORS.REVISION_PANEL).exists()).toBe(false);
        });

        it("shows NotebookRevisionView when selectedRevision is set", async () => {
            const store = setupEditorView();
            store.selectedRevision = {
                id: "rev-1",
                page_id: PAGE_ID,
                content: "# Old content",
                content_format: "markdown",
                edit_source: "user",
                create_time: "2024-01-01T00:00:00",
                update_time: "2024-01-01T00:00:00",
            } as any;
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            expect(wrapper.findComponent(NotebookRevisionView).exists()).toBe(true);
            expect(wrapper.find(SELECTORS.TOOLBAR).exists()).toBe(false);
            expect(wrapper.findComponent(HistoryNotebookEditor).exists()).toBe(false);
        });

        it("revision badge shows count when revisions loaded", async () => {
            const store = setupEditorView();
            store.revisions = [
                { id: "rev-1", page_id: PAGE_ID, edit_source: "user", create_time: "", update_time: "" },
                { id: "rev-2", page_id: PAGE_ID, edit_source: "user", create_time: "", update_time: "" },
            ] as any;
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            const badge = wrapper.find(SELECTORS.REVISIONS_BUTTON + " bbadge-stub");
            expect(badge.exists()).toBe(true);
            expect(badge.text()).toBe("2");
        });

        it("NotebookRevisionView back emits clearSelectedRevision", async () => {
            const store = setupEditorView();
            store.selectedRevision = {
                id: "rev-1",
                page_id: PAGE_ID,
                content: "# Old",
                content_format: "markdown",
                edit_source: "user",
                create_time: "2024-01-01T00:00:00",
                update_time: "2024-01-01T00:00:00",
            } as any;
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            const revView = wrapper.findComponent(NotebookRevisionView);
            revView.vm.$emit("back");
            await wrapper.vm.$nextTick();

            expect(store.clearSelectedRevision).toHaveBeenCalled();
        });

        it("NotebookRevisionView restore calls store.restoreRevision", async () => {
            const store = setupEditorView();
            store.selectedRevision = {
                id: "rev-1",
                page_id: PAGE_ID,
                content: "# Old",
                content_format: "markdown",
                edit_source: "user",
                create_time: "2024-01-01T00:00:00",
                update_time: "2024-01-01T00:00:00",
            } as any;
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            const revView = wrapper.findComponent(NotebookRevisionView);
            revView.vm.$emit("restore", "rev-1");
            await wrapper.vm.$nextTick();

            expect(store.restoreRevision).toHaveBeenCalledWith("rev-1");
        });

        it("revision panel select calls store.loadRevision", async () => {
            const store = setupEditorView();
            store.showRevisions = true;
            store.revisions = [
                { id: "rev-1", page_id: PAGE_ID, edit_source: "user", create_time: "", update_time: "" },
            ] as any;
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            const revList = wrapper.findComponent(NotebookRevisionList);
            revList.vm.$emit("select", "rev-1");
            await wrapper.vm.$nextTick();

            expect(store.loadRevision).toHaveBeenCalledWith("rev-1");
        });
    });

    describe("Chat Panel", () => {
        function setupEditorView() {
            const store = usePageEditorStore();
            store.isLoadingList = false;
            store.isLoadingNotebook = false;
            store.error = null;
            store.currentNotebook = {
                id: PAGE_ID,
                history_id: HISTORY_ID,
                title: "My Notebook",
                content: "# Hello",
                update_time: "2024-01-01T00:00:00",
            } as any;
            store.currentContent = "# Hello";
            store.currentTitle = "My Notebook";
            return store;
        }

        it("shows Chat button in toolbar", async () => {
            setupEditorView();
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            const chatBtn = wrapper.find(SELECTORS.CHAT_BUTTON);
            expect(chatBtn.exists()).toBe(true);
            expect(chatBtn.text()).toContain("Chat");
        });

        it("clicking Chat button calls store.toggleChatPanel", async () => {
            const store = setupEditorView();
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            const chatBtn = wrapper.find(SELECTORS.CHAT_BUTTON);
            await chatBtn.trigger("click");
            await flushPromises();

            expect(store.toggleChatPanel).toHaveBeenCalled();
        });

        it("renders split view when store.showChatPanel is true", async () => {
            const store = setupEditorView();
            store.showChatPanel = true;
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            expect(wrapper.findComponent(HistoryNotebookSplit).exists()).toBe(true);
            expect(wrapper.findComponent(NotebookChatPanel).exists()).toBe(true);
        });

        it("hides split view when store.showChatPanel is false", async () => {
            const store = setupEditorView();
            store.showChatPanel = false;
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            expect(wrapper.findComponent(HistoryNotebookSplit).exists()).toBe(false);
        });

        it("hides Chat button when llm_api_configured is false", async () => {
            setupEditorView();
            mockConfig.value = { llm_api_configured: false };
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            expect(wrapper.find(SELECTORS.CHAT_BUTTON).exists()).toBe(false);
        });

        it("shows Chat button when llm_api_configured is true", async () => {
            setupEditorView();
            mockConfig.value = { llm_api_configured: true };
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            expect(wrapper.find(SELECTORS.CHAT_BUTTON).exists()).toBe(true);
        });

        it("hides Chat button when config is null (not yet loaded)", async () => {
            setupEditorView();
            mockConfig.value = null;
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            expect(wrapper.find(SELECTORS.CHAT_BUTTON).exists()).toBe(false);
        });

        it("passes notebook props to NotebookChatPanel", async () => {
            const store = setupEditorView();
            store.showChatPanel = true;
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            const panel = wrapper.findComponent(NotebookChatPanel);
            expect(panel.props("historyId")).toBe(HISTORY_ID);
            expect(panel.props("pageId")).toBe(PAGE_ID);
            expect(panel.props("notebookContent")).toBe("# Hello");
        });
    });
});
