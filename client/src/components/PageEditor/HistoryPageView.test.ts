import { createTestingPinia } from "@pinia/testing";
import { getFakePageDetails, getFakePageSummary } from "@tests/test-data/pages";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import type { Pinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type * as VueRouter from "vue-router";

import type { HistoryPageSummary } from "@/api/pages";
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
vi.mock("vue-router", async (importOriginal) => {
    const actual = await importOriginal<typeof VueRouter>();
    return {
        ...actual,
        useRouter: vi.fn(() => ({
            push: mockPush,
        })),
        useRoute: vi.fn(() => ({
            params: {},
        })),
    };
});

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

enableAutoUnmount(afterEach);

const HISTORY_ID = "history-1";
const PAGE_ID = "page-1";

const SELECTORS = {
    INFO_ALERT: "g-alert-stub[variant='info']",
    ERROR_ALERT: "g-alert-stub[variant='danger']",
} as const;

let pinia: Pinia;

async function mountComponent(props: { historyId: string; pageId?: string; displayOnly?: boolean }) {
    const wrapper = shallowMount(HistoryPageView as object, {
        props,
        global: withPlugins(getLocalVue(), pinia),
    });
    await flushPromises();
    return wrapper;
}

function setupListViewStore(pages: HistoryPageSummary[] = []) {
    const store = usePageEditorStore();
    store.isLoadingList = false;
    store.error = null;
    store.pages = pages;
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
            const wrapper = await mountComponent({ historyId: HISTORY_ID });

            const alerts = wrapper.findAll(SELECTORS.INFO_ALERT);
            const loadingAlert = alerts.find((w) => w.text().includes("Loading galaxy notebooks"));
            expect(loadingAlert).toBeTruthy();
        });
    });

    describe("Error state", () => {
        it("shows error alert when store.error is set", async () => {
            const store = usePageEditorStore();
            store.isLoadingList = false;
            store.error = "Something went wrong";
            const wrapper = await mountComponent({ historyId: HISTORY_ID });

            const errorAlert = wrapper.find(SELECTORS.ERROR_ALERT);
            expect(errorAlert.exists()).toBe(true);
            expect(errorAlert.text()).toContain("Something went wrong");
        });

        it("keeps PageEditorView mounted when error appears in edit mode", async () => {
            const store = usePageEditorStore();
            store.isLoadingList = false;
            store.error = "Save failed";
            const wrapper = await mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });

            // Outer error alert is suppressed in edit mode — ownership belongs to PageEditorView
            // (otherwise the same store.error renders twice). The editor must stay mounted.
            expect(wrapper.find(SELECTORS.ERROR_ALERT).exists()).toBe(false);
            expect(wrapper.findComponent(PageEditorView).exists()).toBe(true);
        });

        it("shows error alert in display-only mode (editor not mounted)", async () => {
            const store = usePageEditorStore();
            store.isLoadingList = false;
            store.error = "Load failed";
            const wrapper = await mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID, displayOnly: true });

            expect(wrapper.find(SELECTORS.ERROR_ALERT).exists()).toBe(true);
            expect(wrapper.findComponent(PageEditorView).exists()).toBe(false);
        });
    });

    describe("List view (no pageId)", () => {
        it("shows HistoryPageList when no pageId and not loading/error", async () => {
            setupListViewStore();
            const wrapper = await mountComponent({ historyId: HISTORY_ID });

            expect(wrapper.findComponent(HistoryPageList).exists()).toBe(true);
        });

        it("passes store.pages to HistoryPageList", async () => {
            const fakePages = [
                getFakePageSummary({
                    id: "nb-1",
                    history_id: HISTORY_ID,
                    title: "NB1",
                    create_time: "",
                    update_time: "",
                }),
            ];
            setupListViewStore(fakePages);
            const wrapper = await mountComponent({ historyId: HISTORY_ID });

            const list = wrapper.findComponent(HistoryPageList);
            expect(list.props("pages")).toEqual(fakePages);
        });
    });

    describe("Edit mode delegation", () => {
        it("renders PageEditorView when pageId set and not displayOnly", async () => {
            setupListViewStore();
            const wrapper = await mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });

            expect(wrapper.findComponent(PageEditorView).exists()).toBe(true);
        });

        it("passes pageId and historyId to PageEditorView", async () => {
            setupListViewStore();
            const wrapper = await mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });

            const editor = wrapper.findComponent(PageEditorView);
            expect(editor.props("pageId")).toBe(PAGE_ID);
            expect(editor.props("historyId")).toBe(HISTORY_ID);
        });

        it("does not render PageEditorView in displayOnly mode", async () => {
            const store = usePageEditorStore();
            store.isLoadingList = false;
            store.error = null;
            store.currentPage = getFakePageDetails({
                id: PAGE_ID,
                history_id: HISTORY_ID,
                title: "NB",
                content: "# Hello",
                update_time: "2024-01-01T00:00:00",
                username: "",
            });
            store.currentContent = "# Hello";
            store.currentTitle = "NB";
            const wrapper = await mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID, displayOnly: true });

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
            store.currentPage = getFakePageDetails({
                id: PAGE_ID,
                history_id: HISTORY_ID,
                title: "My Page",
                content: "# Hello",
                update_time: "2024-01-01T00:00:00",
                username: "",
            });
            store.currentContent = "# Hello";
            store.currentTitle = "My Page";
            return store;
        }

        it("renders PageDisplayOnly when displayOnly is true", async () => {
            setupLoadedPage();
            const wrapper = await mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID, displayOnly: true });

            expect(wrapper.findComponent(PageDisplayOnly).exists()).toBe(true);
        });

        it("passes correct markdownConfig to PageDisplayOnly", async () => {
            setupLoadedPage();
            const wrapper = await mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID, displayOnly: true });

            const md = wrapper.findComponent(PageDisplayOnly);
            expect(md.props("markdownConfig")).toMatchObject({ id: PAGE_ID, title: "My Page", content: "# Hello" });
        });

        it("Edit button navigates to edit mode (no displayOnly)", async () => {
            setupLoadedPage();
            const wrapper = await mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID, displayOnly: true });

            wrapper.findComponent(PageDisplayOnly).vm.$emit("edit");

            expect(mockPush).toHaveBeenCalledWith(`/histories/${HISTORY_ID}/pages/${PAGE_ID}`);
        });

        it("list view renders normally regardless of displayOnly", async () => {
            setupListViewStore();
            const wrapper = await mountComponent({ historyId: HISTORY_ID, displayOnly: true });

            expect(wrapper.findComponent(HistoryPageList).exists()).toBe(true);
        });

        it("does not clear editor state on unmount in displayOnly mode", async () => {
            setupLoadedPage();
            const store = usePageEditorStore();
            const wrapper = await mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID, displayOnly: true });

            wrapper.unmount();
            expect(store.$reset).not.toHaveBeenCalled();
            expect(store.clearCurrentPage).not.toHaveBeenCalled();
        });
    });

    describe("Navigation/Events", () => {
        it("edit emit from list navigates to page edit URL", async () => {
            setupListViewStore([
                getFakePageSummary({ id: "nb-1", history_id: HISTORY_ID, title: "NB1", username: "" }),
            ]);
            const wrapper = await mountComponent({ historyId: HISTORY_ID });

            const list = wrapper.findComponent(HistoryPageList);
            list.vm.$emit("edit", "nb-1");
            await wrapper.vm.$nextTick();

            expect(mockPush).toHaveBeenCalledWith(`/histories/${HISTORY_ID}/pages/nb-1`);
        });

        it("handleCreate calls store.createPage and navigates on success", async () => {
            const store = setupListViewStore();
            vi.mocked(store.createPage).mockResolvedValue(
                getFakePageDetails({
                    id: "new-page",
                    history_id: HISTORY_ID,
                    title: "Untitled Page",
                    content: "",
                    username: "",
                }),
            );
            const wrapper = await mountComponent({ historyId: HISTORY_ID });

            const list = wrapper.findComponent(HistoryPageList);
            list.vm.$emit("create");
            await flushPromises();

            expect(store.createPage).toHaveBeenCalledWith({ title: undefined, content: undefined });
            expect(mockPush).toHaveBeenCalledWith(`/histories/${HISTORY_ID}/pages/new-page`);
        });

        it("view emit from list navigates to displayOnly URL via pushToFrameOrPage", async () => {
            setupListViewStore([
                getFakePageSummary({ id: "nb-1", history_id: HISTORY_ID, title: "NB1", username: "" }),
            ]);
            const wrapper = await mountComponent({ historyId: HISTORY_ID });

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
            setupListViewStore([
                getFakePageSummary({ id: "nb-1", history_id: HISTORY_ID, title: "NB1", username: "" }),
            ]);
            const wrapper = await mountComponent({ historyId: HISTORY_ID });

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
            await mountComponent({ historyId: HISTORY_ID });

            expect(store.loadPages).toHaveBeenCalledWith(HISTORY_ID, undefined);
        });

        it("does not call store.loadPageById on mount when no pageId", async () => {
            const store = usePageEditorStore();
            await mountComponent({ historyId: HISTORY_ID });

            expect(store.loadPageById).not.toHaveBeenCalled();
        });

        it("calls store.loadPageById on mount when pageId and displayOnly", async () => {
            const store = usePageEditorStore();
            await mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID, displayOnly: true });

            expect(store.loadPageById).toHaveBeenCalledWith(PAGE_ID);
        });

        it("does not call store.loadPageById on mount when pageId but not displayOnly", async () => {
            const store = usePageEditorStore();
            await mountComponent({ historyId: HISTORY_ID, pageId: PAGE_ID });

            // Edit mode delegates loading to PageEditorView
            expect(store.loadPageById).not.toHaveBeenCalled();
        });

        it("calls store.$reset on unmount", async () => {
            const store = usePageEditorStore();
            const wrapper = await mountComponent({ historyId: HISTORY_ID });

            wrapper.unmount();
            expect(store.$reset).toHaveBeenCalled();
        });
    });
});
