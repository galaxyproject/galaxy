import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import type { PasteContentItem, PasteUrlItem } from "@/components/Panels/Upload/types/uploadItem";
import { useHasStagedUploads } from "@/composables/upload/useUploadStaging";
import { useUploadStagingStore } from "@/stores/uploadStagingStore";

describe("useHasStagedUploads", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    it("is false when nothing is staged", () => {
        const hasStagedUploads = useHasStagedUploads();
        expect(hasStagedUploads.value).toBe(false);
    });

    it("is true when any method has staged items and false again once cleared", () => {
        const store = useUploadStagingStore();
        const hasStagedUploads = useHasStagedUploads();

        store.setItems("paste-links", [{ url: "https://example.org/a.txt" } as PasteUrlItem]);
        expect(hasStagedUploads.value).toBe(true);

        store.clearItems("paste-links");
        expect(hasStagedUploads.value).toBe(false);
    });

    it("ignores blank pasted content", () => {
        const store = useUploadStagingStore();
        const hasStagedUploads = useHasStagedUploads();

        store.setItems("paste-content", [{ content: "   " } as PasteContentItem]);
        expect(hasStagedUploads.value).toBe(false);

        store.setItems("paste-content", [{ content: "data" } as PasteContentItem]);
        expect(hasStagedUploads.value).toBe(true);
    });
});
