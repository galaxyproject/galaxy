import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import type { Pinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { HistoryPageDetails, PageRevisionSummary } from "@/api/pages.js";
import { usePageEditorStore } from "@/stores/pageEditorStore";

import { PAGE_LABELS } from "../Page/constants.js";

import PageDisplayToolbar from "./PageDisplayToolbar.vue";

const localVue = getLocalVue();

const HISTORY_ID = "history-1";
const PAGE_ID = "page-1";

const SELECTORS = {
    EDITOR_TOOLBAR: "[data-description='page editor toolbar']",
    DISPLAY_TOOLBAR: "[data-description='page display toolbar']",
    TOOLBAR_TITLE: "[data-description='page editor title']",
    SAVE_BUTTON: "[data-description='page save button']",
    BACK_BUTTON: "[data-description='page back button']",
    UNSAVED_INDICATOR: "[data-description='page unsaved indicator']",
    REVISIONS_BUTTON: "[data-description='page revisions button']",
    REVISIONS_BADGE: "[data-description='page revision count badge']",
    EDIT_BUTTON: "[data-description='page edit button']",
    RENAME_BUTTON: "[data-description='page rename button']",
    RENAME_INPUT: "[data-description='galaxy notebook name input']",
    PREVIEW_BUTTON: "[data-description='page preview button']",
} as const;

let pinia: Pinia;

function mountComponent(propsData: {
    labels: (typeof PAGE_LABELS)[keyof typeof PAGE_LABELS];
    mode: "editor" | "display";
}) {
    return mount(PageDisplayToolbar as object, {
        localVue,
        propsData,
        pinia,
    });
}

describe("PageDisplayToolbar", () => {
    function setupLoadedPage() {
        const newStore = usePageEditorStore();
        newStore.isLoadingList = false;
        newStore.isLoadingPage = false;
        newStore.error = null;
        newStore.currentPage = {
            id: PAGE_ID,
            history_id: HISTORY_ID,
            title: "My Page",
            content: "# Hello",
            update_time: "2024-01-01T00:00:00",
        } as HistoryPageDetails;
        newStore.currentContent = "# Hello";
        newStore.currentTitle = "My Page";
        newStore.revisions = [
            { id: "rev-1", page_id: PAGE_ID, edit_source: "user", create_time: "", update_time: "" },
            { id: "rev-2", page_id: PAGE_ID, edit_source: "user", create_time: "", update_time: "" },
        ] as PageRevisionSummary[];
        return newStore;
    }

    let wrapper: Wrapper<Vue>;
    let store: ReturnType<typeof usePageEditorStore>;

    beforeEach(async () => {
        pinia = createTestingPinia({ createSpy: vi.fn });
        store = setupLoadedPage();
        await flushPromises();
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe("editor mode", () => {
        beforeEach(async () => {
            wrapper = mountComponent({ labels: PAGE_LABELS.history, mode: "editor" });
            await flushPromises();
        });

        it("shows edit toolbar with Edit button pressed", async () => {
            expect(wrapper.find(SELECTORS.EDITOR_TOOLBAR).exists()).toBe(true);

            expect(wrapper.find(SELECTORS.EDIT_BUTTON).props("pressed")).toBe(true);
            expect(wrapper.find(SELECTORS.PREVIEW_BUTTON).props("pressed")).toBe(false);
        });

        it("shows rename button and page title in toolbar", () => {
            expect(wrapper.find(SELECTORS.RENAME_BUTTON).exists()).toBe(true);
            expect(wrapper.find(SELECTORS.TOOLBAR_TITLE).text()).toBe("My Page");
        });

        it("shows 'Untitled Notebook' in title when currentTitle is empty", async () => {
            store.currentTitle = "";
            await wrapper.vm.$nextTick();

            expect(wrapper.find(SELECTORS.TOOLBAR_TITLE).text()).toBe("Untitled Notebook");
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
            expect(saveBtn.attributes("aria-disabled")).toBe("true");
        });

        it("shows Preview button in toolbar", () => {
            const previewBtn = wrapper.find(SELECTORS.PREVIEW_BUTTON);
            expect(previewBtn.exists()).toBe(true);
            expect(previewBtn.text()).toContain("Preview");
        });

        it("Preview button emits a preview event", async () => {
            const previewBtn = wrapper.find(SELECTORS.PREVIEW_BUTTON);
            await previewBtn.trigger("click");

            expect(wrapper.emitted("preview")).toHaveLength(1);
        });

        it("rename button opens rename modal which renames the page", async () => {
            expect(wrapper.find(SELECTORS.RENAME_BUTTON).exists()).toBe(true);

            const renameBtn = wrapper.find(SELECTORS.RENAME_BUTTON);
            await renameBtn.trigger("click");
            await wrapper.vm.$nextTick();

            const renameInput = wrapper.find(SELECTORS.RENAME_INPUT);
            expect(renameInput.exists()).toBe(true);
            expect((renameInput.element as HTMLInputElement).value).toBe("My Page");

            (renameInput.element as HTMLInputElement).value = "Renamed Page";
            await renameInput.trigger("input");

            const renameBtnInModal = wrapper.find(".g-modal-confirm-buttons .g-blue");
            await renameBtnInModal.trigger("click");
            await wrapper.vm.$nextTick();

            expect(store.updateTitle).toHaveBeenCalledWith("Renamed Page");
        });

        it("back button emits a back event", async () => {
            const backBtn = wrapper.find(SELECTORS.BACK_BUTTON);
            await backBtn.trigger("click");

            expect(wrapper.emitted("back")).toHaveLength(1);
        });

        it("save button calls store.savePage", async () => {
            const saveBtn = wrapper.find(SELECTORS.SAVE_BUTTON);
            await saveBtn.trigger("click");
            await flushPromises();

            expect(store.savePage).toHaveBeenCalled();
        });

        it("back button text says whatever the label back button value is", () => {
            const backBtn = wrapper.find(SELECTORS.BACK_BUTTON);
            expect(backBtn.text()).toContain(PAGE_LABELS.history.editorBackLabel);
        });

        describe("revisions", () => {
            it("shows Revisions button in toolbar", () => {
                const revBtn = wrapper.find(SELECTORS.REVISIONS_BUTTON);
                expect(revBtn.exists()).toBe(true);
                expect(revBtn.text()).toContain("Revisions");
            });

            it("clicking Revisions button calls store.toggleRevisions", async () => {
                const revBtn = wrapper.find(SELECTORS.REVISIONS_BUTTON);
                await revBtn.trigger("click");

                expect(store.toggleRevisions).toHaveBeenCalled();
            });

            it("revision badge shows count when revisions loaded", () => {
                const badge = wrapper.find(SELECTORS.REVISIONS_BADGE);
                expect(badge.exists()).toBe(true);
                expect(badge.text()).toBe("2");
            });
        });
    });

    describe("display mode", () => {
        beforeEach(async () => {
            wrapper = mountComponent({ labels: PAGE_LABELS.history, mode: "display" });
            await flushPromises();
        });

        it("shows display toolbar with Preview button pressed", async () => {
            expect(wrapper.find(SELECTORS.DISPLAY_TOOLBAR).exists()).toBe(true);

            expect(wrapper.find(SELECTORS.EDIT_BUTTON).props("pressed")).toBe(false);
            expect(wrapper.find(SELECTORS.PREVIEW_BUTTON).props("pressed")).toBe(true);
        });

        it("Edit button emits an edit event", async () => {
            const editBtn = wrapper.find(SELECTORS.EDIT_BUTTON);
            await editBtn.trigger("click");
            await wrapper.vm.$nextTick();

            expect(wrapper.emitted("edit")).toHaveLength(1);
        });
    });
});
