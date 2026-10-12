import { runInTestScope } from "@tests/vitest/effectScope";
import { createPinia, disposePinia, setActivePinia } from "pinia";
import { describe, expect, it, onTestFinished } from "vitest";

import type { BaseUploadItem, PasteContentItem, PasteUrlItem } from "@/components/Panels/Upload/types/uploadItem";
import { useHasStagedUploads } from "@/composables/upload/useUploadStaging";
import { useUploadStagingStore } from "@/stores/uploadStagingStore";

const uploadDefaults: BaseUploadItem = {
    name: "staged upload",
    extension: "auto",
    dbkey: "?",
    spaceToTab: false,
    toPosixLines: false,
    autoDecompress: true,
};

function createPastedContent(content: string): PasteContentItem {
    return { ...uploadDefaults, id: 1, content };
}

function setupStaging() {
    const pinia = createPinia();
    setActivePinia(pinia);
    onTestFinished(() => disposePinia(pinia));

    return {
        store: useUploadStagingStore(pinia),
        hasStagedUploads: runInTestScope(useHasStagedUploads),
    };
}

describe("useHasStagedUploads", () => {
    it("is false when nothing is staged", () => {
        const { hasStagedUploads } = setupStaging();
        expect(hasStagedUploads.value).toBe(false);
    });

    it("is true when a pasted link is staged and false again once cleared", () => {
        const { store, hasStagedUploads } = setupStaging();

        const pastedUrl: PasteUrlItem = {
            ...uploadDefaults,
            id: 1,
            deferred: false,
            url: "https://example.org/a.txt",
        };

        store.setItems("paste-links", [pastedUrl]);
        expect(hasStagedUploads.value).toBe(true);

        store.clearItems("paste-links");
        expect(hasStagedUploads.value).toBe(false);
    });

    it("ignores blank pasted content and detects its replacement with data", () => {
        const { store, hasStagedUploads } = setupStaging();

        store.setItems("paste-content", [createPastedContent("   ")]);
        expect(hasStagedUploads.value).toBe(false);

        store.setItems("paste-content", [createPastedContent("data")]);
        expect(hasStagedUploads.value).toBe(true);
    });
});
