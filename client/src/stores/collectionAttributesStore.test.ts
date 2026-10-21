import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DatasetCollectionAttributes } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";

import { useCollectionAttributesStore } from "./collectionAttributesStore";
import { setupTestPinia } from "./testUtils";

const COLLECTION_ID = "123";

const ATTRIBUTES: DatasetCollectionAttributes = {
    dbkey: "hg19",
    extension: "bed",
    model_class: "HistoryDatasetCollectionAssociation",
    dbkeys: ["hg19", "hg38"],
    extensions: ["bed", "vcf"],
    tags: ["tag1", "tag2"],
};

const attributesRequest = vi.fn();

const { server, http } = useServerMock();

describe("collectionAttributesStore", () => {
    beforeEach(() => {
        setupTestPinia();
        attributesRequest.mockClear();

        server.use(
            http.get("/api/dataset_collections/{hdca_id}/attributes", ({ params, response }) => {
                attributesRequest(params.hdca_id);
                return response(200).json(ATTRIBUTES);
            }),
        );
    });

    it("fetches missing attributes and clears loading after caching them", async () => {
        const store = useCollectionAttributesStore();
        expect(store.storedAttributes[COLLECTION_ID]).toBeUndefined();
        expect(store.isLoadingAttributes(COLLECTION_ID)).toBe(false);

        const result = store.getAttributes(COLLECTION_ID);

        expect(result).toBeNull();
        expect(store.isLoadingAttributes(COLLECTION_ID)).toBe(true);
        await flushPromises();
        expect(store.isLoadingAttributes(COLLECTION_ID)).toBe(false);

        expect(store.storedAttributes[COLLECTION_ID]).toEqual(ATTRIBUTES);
        expect(attributesRequest).toHaveBeenCalledExactlyOnceWith(COLLECTION_ID);
    });

    it("returns cached attributes without requesting them again", async () => {
        const store = useCollectionAttributesStore();

        store.storedAttributes[COLLECTION_ID] = ATTRIBUTES;

        const result = store.getAttributes(COLLECTION_ID);
        await flushPromises();

        expect(result).toEqual(ATTRIBUTES);
        expect(attributesRequest).not.toHaveBeenCalled();
    });
});
