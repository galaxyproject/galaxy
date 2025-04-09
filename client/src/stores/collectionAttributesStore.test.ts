import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";

import { type DatasetCollectionAttributes } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";

import { useCollectionAttributesStore } from "./collectionAttributesStore";

const FAKE_HDCA_ID = "123";

const FAKE_ATTRIBUTES: DatasetCollectionAttributes = {
    dbkey: "hg19",
    extension: "bed",
    model_class: "HistoryDatasetCollectionAssociation",
    dbkeys: ["hg19", "hg38"],
    extensions: ["bed", "vcf"],
    tags: ["tag1", "tag2"],
};

const fetchCollectionAttributesMock = jest.fn().mockReturnValue(FAKE_ATTRIBUTES);

const { server, http } = useServerMock();

describe("collectionAttributesStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());

        server.use(
            http.get("/api/dataset_collections/{hdca_id}/attributes", ({ response }) => {
                return response(200).json(fetchCollectionAttributesMock());
            })
        );
    });

    it("should fetch attributes and store them", async () => {
        const store = useCollectionAttributesStore();
        expect(store.storedAttributes[FAKE_HDCA_ID]).toBeUndefined();
        expect(store.isLoadingAttributes(FAKE_HDCA_ID)).toBeFalsy();

        store.getAttributes(FAKE_HDCA_ID);
        // getAttributes will trigger a fetch if the attributes are not stored
        expect(store.isLoadingAttributes(FAKE_HDCA_ID)).toBeTruthy();
        await flushPromises();
        expect(store.isLoadingAttributes(FAKE_HDCA_ID)).toBeFalsy();

        expect(store.storedAttributes[FAKE_HDCA_ID]).toEqual(FAKE_ATTRIBUTES);
        expect(fetchCollectionAttributesMock).toHaveBeenCalled();
    });

    it("should not fetch attributes if already stored", async () => {
        const store = useCollectionAttributesStore();

        store.storedAttributes[FAKE_HDCA_ID] = FAKE_ATTRIBUTES;

        const result = store.getAttributes(FAKE_HDCA_ID);

        expect(result).toEqual(FAKE_ATTRIBUTES);
        expect(fetchCollectionAttributesMock).not.toHaveBeenCalled();
    });
});
