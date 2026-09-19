import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import type { Pinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { usePageEditorStore } from "@/stores/pageEditorStore";

import HistoryPageList from "./HistoryPageList.vue";
import HistoryPageView from "./HistoryPageView.vue";
import PageDisplayOnly from "./PageDisplayOnly.vue";
import PageEditorView from "./PageEditorView.vue";

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(() => ({
        config: { value: { llm_api_configured: true } },
        isConfigLoaded: { value: true },
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

const mockPushToFrameOrPage = vi.fn();
vi.mock("@/composables/windowAwareNavigation", () => ({
    useWindowAwareNavigation: vi.fn(() => ({
        pushToFrameOrPage: mockPushToFrameOrPage,
    })),
}));

vi.mock("@/composables/confirmDialog.js", () => ({
    useConfirmDialog: vi.fn(() => ({
        confirm: vi.fn().mockResolvedValue(true),
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
} as const;

let pinia: Pinia;

function mountComponent(propsData: { historyId: string; pageId?: string; displayOnly?: boolean }) {
    return shallowMount(HistoryPageView as object, {
        localVue,
        propsData,
        pinia,
    });
}

function setupListViewStore(pages: any[] = []) {
    const store = usePageEditorStore();
    store.isLoadingList = false;
    store.error = null;
    store.pages = pages as any;
    return store;
}

describe("HistoryPageView", () => {
    beforeEach(() => {
        pinia = createTestingPinia({ createSpy: vi.fn });
        vi.clearAllMocks();
        mockPushToFrameOrPage.mockReset();
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
            const loadingAlert = alerts.wrappers.find((w) => w.text().includes("Loading galaxy notebooks"));
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

        it("keeps PageEditorView mounted when error appears in edit mode", async () => {
            const store = usePageEditorStore();
            store.isLoadingList = false;
            store.error = "Save failed";
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            // Outer error alert is suppressed in edit mode — ownership belongs to PageEditorView
            // (otherwise the same store.error renders twice). The editor must stay mounted.
            expect(wrapper.find(SELECTORS.ERROR_ALERT).exists()).toBe(false);
            expect(wrapper.findComponent(PageEditorView).exists()).toBe(true);
        });

        it("shows error alert in display-only mode (editor not mounted)", async () => {
            const store = usePageEditorStore();
            store.isLoadingList = false;
            store.error = "Load failed";
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID, displayOnly: true });
            await flushPromises();

            expect(wrapper.find(SELECTORS.ERROR_ALERT).exists()).toBe(true);
            expect(wrapper.findComponent(PageEditorView).exists()).toBe(false);
        });
    });

    describe("List view (no pageId)", () => {
        it("shows HistoryPageList when no pageId and not loading/error", async () => {
            setupListViewStore();
            const wrapper = mountComponent({ historyId: HISTORY_ID });
            await flushPromises();

            expect(wrapper.findComponent(HistoryPageList).exists()).toBe(true);
        });

        it("passes store.pages to HistoryPageList", async () => {
            const fakePages = [
                { id: "nb-1", history_id: HISTORY_ID, title: "NB1", deleted: false, create_time: "", update_time: "" },
            ];
            setupListViewStore(fakePages);
            const wrapper = mountComponent({ historyId: HISTORY_ID });
            await flushPromises();

            const list = wrapper.findComponent(HistoryPageList);
            expect(list.props("pages")).toEqual(fakePages);
        });
    });

    describe("Edit mode delegation", () => {
        it("renders PageEditorView when pageId set and not displayOnly", async () => {
            setupListViewStore();
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            expect(wrapper.findComponent(PageEditorView).exists()).toBe(true);
        });

        it("passes pageId and historyId to PageEditorView", async () => {
            setupListViewStore();
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            const editor = wrapper.findComponent(PageEditorView);
            expect(editor.props("pageId")).toBe(PAGE_ID);
            expect(editor.props("historyId")).toBe(HISTORY_ID);
        });

        it("does not render PageEditorView in displayOnly mode", async () => {
            const store = usePageEditorStore();
            store.isLoadingList = false;
            store.error = null;
            store.currentPage = {
                id: PAGE_ID,
                history_id: HISTORY_ID,
                title: "NB",
                content: "# Hello",
                update_time: "2024-01-01T00:00:00",
            } as any;
            store.currentContent = "# Hello";
            store.currentTitle = "NB";
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID, displayOnly: true });
            await flushPromises();

            expect(wrapper.findComponent(PageEditorView).exists()).toBe(false);
            expect(wrapper.findComponent(PageDisplayOnly).exists()).toBe(true);
        });
    });

    describe("DisplayOnly mode", () => {
        function setupLoadedPage() {
            const store = usePageEditorStore();
            store.isLoadingList = false;
            store.isLoadingPage = false;
            store.error = null;
            store.currentPage = {
                id: PAGE_ID,
                history_id: HISTORY_ID,
                title: "My Page",
                content: "# Hello",
                update_time: "2024-01-01T00:00:00",
            } as any;
            store.currentContent = "# Hello";
            store.currentTitle = "My Page";
            // hasCurrentPage is a computed (readonly) — stub it so the display toolbar renders
            vi.spyOn(store, "hasCurrentPage", "get").mockReturnValue(true);
            return store;
        }

        it("renders Markdown when displayOnly is true", async () => {
            setupLoadedPage();
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID, displayOnly: true });
            await flushPromises();

            expect(wrapper.findComponent(PageDisplayOnly).exists()).toBe(true);
        });

        it("passes correct markdownConfig to PageDisplayOnly", async () => {
            setupLoadedPage();
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID, displayOnly: true });
            await flushPromises();

            const md = wrapper.findComponent(PageDisplayOnly);
            const config = md.props("markdownConfig");
            expect(config.id).toBe(PAGE_ID);
            expect(config.title).toBe("My Page");
            expect(config.content).toBe("# Hello");
        });

        it("Edit button navigates to edit mode (no displayOnly)", async () => {
            setupLoadedPage();
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID, displayOnly: true });
            await flushPromises();

            wrapper.findComponent(PageDisplayOnly).vm.$emit("edit");

            expect(mockPush).toHaveBeenCalledWith(`/histories/${HISTORY_ID}/pages/${PAGE_ID}`);
        });

        it("list view renders normally regardless of displayOnly", async () => {
            setupListViewStore();
            const wrapper = mountComponent({ historyId: HISTORY_ID, displayOnly: true });
            await flushPromises();

            expect(wrapper.findComponent(HistoryPageList).exists()).toBe(true);
        });

        it("does not clear editor state on unmount in displayOnly mode", async () => {
            setupLoadedPage();
            const store = usePageEditorStore();
            const wrapper = mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID, displayOnly: true });
            await flushPromises();

            wrapper.destroy();
            expect(store.$reset).not.toHaveBeenCalled();
            expect(store.clearCurrentPage).not.toHaveBeenCalled();
        });
    });

    describe("Navigation/Events", () => {
        it("edit emit from list navigates to page edit URL", async () => {
            setupListViewStore([{ id: "nb-1", history_id: HISTORY_ID, title: "NB1" }]);
            const wrapper = mountComponent({ historyId: HISTORY_ID });
            await flushPromises();

            const list = wrapper.findComponent(HistoryPageList);
            list.vm.$emit("edit", "nb-1");
            await wrapper.vm.$nextTick();

            expect(mockPush).toHaveBeenCalledWith(`/histories/${HISTORY_ID}/pages/nb-1`);
        });

        it("handleCreate calls store.createPage and navigates on success", async () => {
            const store = setupListViewStore();
            vi.mocked(store.createPage).mockResolvedValue({
                id: "new-page",
                history_id: HISTORY_ID,
                title: "Untitled Page",
                content: "",
            } as any);
            const wrapper = mountComponent({ historyId: HISTORY_ID });
            await flushPromises();

            const list = wrapper.findComponent(HistoryPageList);
            list.vm.$emit("create");
            await flushPromises();

            expect(store.createPage).toHaveBeenCalledWith({ title: undefined, content: undefined });
            expect(mockPush).toHaveBeenCalledWith(`/histories/${HISTORY_ID}/pages/new-page`);
        });

        it("view emit from list navigates to displayOnly URL via pushToFrameOrPage", async () => {
            setupListViewStore([{ id: "nb-1", history_id: HISTORY_ID, title: "NB1" }]);
            const wrapper = mountComponent({ historyId: HISTORY_ID });
            await flushPromises();

            const list = wrapper.findComponent(HistoryPageList);
            list.vm.$emit("view", "nb-1");
            await wrapper.vm.$nextTick();

            expect(mockPushToFrameOrPage).toHaveBeenCalledWith(
                expect.objectContaining({
                    inlineUrl: `/histories/${HISTORY_ID}/pages/nb-1?displayOnly=true`,
                }),
            );
        });
    });

    describe("Window Manager integration", () => {
        afterEach(() => {
            mockGalaxyInstance.frame.active = false;
        });

        it("view emit opens in WinBox when WM is active", async () => {
            mockGalaxyInstance.frame.active = true;
            setupListViewStore([{ id: "nb-1", history_id: HISTORY_ID, title: "NB1" }]);
            const wrapper = mountComponent({ historyId: HISTORY_ID });
            await flushPromises();

            const list = wrapper.findComponent(HistoryPageList);
            list.vm.$emit("view", "nb-1");
            await wrapper.vm.$nextTick();

            expect(mockPushToFrameOrPage).toHaveBeenCalledWith(
                expect.objectContaining({
                    inlineUrl: `/histories/${HISTORY_ID}/pages/nb-1?displayOnly=true`,
                    title: "Galaxy Notebook: NB1",
                }),
            );
        });
    });

    describe("Lifecycle", () => {
        it("calls store.loadPages on mount", async () => {
            const store = usePageEditorStore();
            mountComponent({ historyId: HISTORY_ID });
            await flushPromises();

            expect(store.loadPages).toHaveBeenCalledWith(HISTORY_ID, undefined);
        });

        it("does not call store.loadPageById on mount when no pageId", async () => {
            const store = usePageEditorStore();
            mountComponent({ historyId: HISTORY_ID });
            await flushPromises();

            expect(store.loadPageById).not.toHaveBeenCalled();
        });

        it("calls store.loadPageById on mount when pageId and displayOnly", async () => {
            const store = usePageEditorStore();
            mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID, displayOnly: true });
            await flushPromises();

            expect(store.loadPageById).toHaveBeenCalledWith(PAGE_ID);
        });

        it("does not call store.loadPageById on mount when pageId but not displayOnly", async () => {
            const store = usePageEditorStore();
            mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });
            await flushPromises();

            // Edit mode delegates loading to PageEditorView
            expect(store.loadPageById).not.toHaveBeenCalled();
        });

        it("calls store.$reset on unmount", async () => {
            const store = usePageEditorStore();
            const wrapper = mountComponent({ historyId: HISTORY_ID });
            await flushPromises();

            wrapper.destroy();
            expect(store.$reset).toHaveBeenCalled();
        });
    });
});
