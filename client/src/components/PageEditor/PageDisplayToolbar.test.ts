import { createTestingPinia } from "@pinia/testing";
import { getFakePageDetails, getFakePageRevisionSummary } from "@tests/test-data/pages";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import type GButton from "@/components/BaseComponents/GButton.vue";
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
    RENAME_CONFIRM_BUTTON: ".g-modal-confirm-buttons .g-blue",
    PREVIEW_BUTTON: "[data-description='page preview button']",
} as const;

enableAutoUnmount(afterEach);

/**
 * Mounts the toolbar over a loaded "My Page" with two revisions. Its current title
 * and content differ from the store's never-saved originals, so it starts dirty.
 */
function mountToolbar(mode: "editor" | "display", stubs: Record<string, object> = {}) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    const store = usePageEditorStore();
    store.isLoadingList = false;
    store.isLoadingPage = false;
    store.error = null;
    store.currentPage = getFakePageDetails({
        id: PAGE_ID,
        history_id: HISTORY_ID,
        title: "My Page",
        content: "# Hello",
    });
    store.currentContent = "# Hello";
    store.currentTitle = "My Page";
    store.revisions = [
        getFakePageRevisionSummary({ id: "rev-1", page_id: PAGE_ID }),
        getFakePageRevisionSummary({ id: "rev-2", page_id: PAGE_ID }),
    ];

    const wrapper = mount(PageDisplayToolbar, {
        props: { labels: PAGE_LABELS.history, mode },
        global: { ...withPlugins(localVue, pinia), stubs: { ...localVue.stubs, ...stubs } },
    });
    return { wrapper, store };
}

function mountEditorWithSavedIndicatorSpy() {
    const flashSavedIndicator = vi.fn();
    const mounted = mountToolbar("editor", {
        ChangesIndicator: { template: "<div />", methods: { flashSavedIndicator } },
    });
    return { ...mounted, flashSavedIndicator };
}

describe("PageDisplayToolbar", () => {
    describe("editor mode", () => {
        it("shows the editor toolbar with the Edit button pressed", () => {
            const { wrapper } = mountToolbar("editor");

            expect(wrapper.find(SELECTORS.EDITOR_TOOLBAR).exists()).toBe(true);
            expect(wrapper.findComponent<typeof GButton>(SELECTORS.EDIT_BUTTON).props("pressed")).toBe(true);
            expect(wrapper.findComponent<typeof GButton>(SELECTORS.PREVIEW_BUTTON).props("pressed")).toBe(false);
        });

        it("shows the rename button and the page title", () => {
            const { wrapper } = mountToolbar("editor");

            expect(wrapper.find(SELECTORS.RENAME_BUTTON).exists()).toBe(true);
            expect(wrapper.find(SELECTORS.TOOLBAR_TITLE).text()).toBe("My Page");
        });

        it("shows the default title once the current title is cleared", async () => {
            const { wrapper, store } = mountToolbar("editor");

            store.currentTitle = "";
            await nextTick();

            expect(wrapper.find(SELECTORS.TOOLBAR_TITLE).text()).toBe("Untitled Notebook");
        });

        it("shows the Unsaved indicator while the page has unsaved changes", () => {
            const { wrapper, store } = mountToolbar("editor");

            expect(store.isDirty).toBe(true);
            const unsaved = wrapper.find(SELECTORS.UNSAVED_INDICATOR);
            expect(unsaved.exists()).toBe(true);
            expect(unsaved.text()).toBe("Unsaved");
        });

        it("disables the save button once nothing is left to save", async () => {
            const { wrapper, store } = mountToolbar("editor");

            store.currentContent = "";
            store.currentTitle = "";
            await nextTick();

            expect(store.canSave).toBe(false);
            expect(wrapper.find(SELECTORS.SAVE_BUTTON).attributes("aria-disabled")).toBe("true");
        });

        it("labels the back button with the editor back label", () => {
            const { wrapper } = mountToolbar("editor");

            expect(wrapper.find(SELECTORS.BACK_BUTTON).text()).toContain(PAGE_LABELS.history.editorBackLabel);
        });

        it("emits back when the back button is clicked", async () => {
            const { wrapper } = mountToolbar("editor");

            await wrapper.find(SELECTORS.BACK_BUTTON).trigger("click");

            expect(wrapper.emitted("back")).toHaveLength(1);
        });

        it("shows a Preview button", () => {
            const { wrapper } = mountToolbar("editor");

            const previewButton = wrapper.find(SELECTORS.PREVIEW_BUTTON);
            expect(previewButton.exists()).toBe(true);
            expect(previewButton.text()).toContain("Preview");
        });

        it("emits preview when the Preview button is clicked", async () => {
            const { wrapper } = mountToolbar("editor");

            await wrapper.find(SELECTORS.PREVIEW_BUTTON).trigger("click");

            expect(wrapper.emitted("preview")).toHaveLength(1);
        });

        it("renames the page through the rename modal", async () => {
            const { wrapper, store } = mountToolbar("editor");

            await wrapper.find(SELECTORS.RENAME_BUTTON).trigger("click");
            const renameInput = wrapper.find<HTMLInputElement>(SELECTORS.RENAME_INPUT);
            expect(renameInput.exists()).toBe(true);
            expect(renameInput.element.value).toBe("My Page");

            await renameInput.setValue("Renamed Page");
            await wrapper.find(SELECTORS.RENAME_CONFIRM_BUTTON).trigger("click");

            expect(store.updateTitle).toHaveBeenCalledWith("Renamed Page");
        });

        describe("saving", () => {
            it("saves the page when the save button is clicked", async () => {
                const { wrapper, store } = mountToolbar("editor");

                await wrapper.find(SELECTORS.SAVE_BUTTON).trigger("click");
                await flushPromises();

                expect(store.savePage).toHaveBeenCalled();
            });

            it("flashes the saved indicator after a successful save", async () => {
                const { wrapper, flashSavedIndicator } = mountEditorWithSavedIndicatorSpy();

                await wrapper.find(SELECTORS.SAVE_BUTTON).trigger("click");
                await flushPromises();

                expect(flashSavedIndicator).toHaveBeenCalledOnce();
            });

            it("does not flash the saved indicator after a failed save", async () => {
                const { wrapper, store, flashSavedIndicator } = mountEditorWithSavedIndicatorSpy();
                vi.mocked(store.savePage).mockRejectedValue(new Error("save failed"));

                await wrapper.find(SELECTORS.SAVE_BUTTON).trigger("click");
                await flushPromises();

                expect(flashSavedIndicator).not.toHaveBeenCalled();
            });
        });

        describe("revisions", () => {
            it("shows a Revisions button", () => {
                const { wrapper } = mountToolbar("editor");

                const revisionsButton = wrapper.find(SELECTORS.REVISIONS_BUTTON);
                expect(revisionsButton.exists()).toBe(true);
                expect(revisionsButton.text()).toContain("Revisions");
            });

            it("toggles the revisions panel when the Revisions button is clicked", async () => {
                const { wrapper, store } = mountToolbar("editor");

                await wrapper.find(SELECTORS.REVISIONS_BUTTON).trigger("click");

                expect(store.toggleRevisions).toHaveBeenCalled();
            });

            it("shows the revision count in a badge", () => {
                const { wrapper } = mountToolbar("editor");

                const badge = wrapper.find(SELECTORS.REVISIONS_BADGE);
                expect(badge.exists()).toBe(true);
                expect(badge.text()).toBe("2");
            });
        });
    });

    describe("display mode", () => {
        it("shows the display toolbar with the Preview button pressed", () => {
            const { wrapper } = mountToolbar("display");

            expect(wrapper.find(SELECTORS.DISPLAY_TOOLBAR).exists()).toBe(true);
            expect(wrapper.findComponent<typeof GButton>(SELECTORS.EDIT_BUTTON).props("pressed")).toBe(false);
            expect(wrapper.findComponent<typeof GButton>(SELECTORS.PREVIEW_BUTTON).props("pressed")).toBe(true);
        });

        it("emits edit when the Edit button is clicked", async () => {
            const { wrapper } = mountToolbar("display");

            await wrapper.find(SELECTORS.EDIT_BUTTON).trigger("click");

            expect(wrapper.emitted("edit")).toHaveLength(1);
        });
    });
});
