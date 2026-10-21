import type { HDCASummary } from "@/api";

export function getFakeCollectionSummary(overrides: Partial<HDCASummary> = {}): HDCASummary {
    const id = overrides.id ?? "collection-id";
    return {
        id: id,
        element_count: 10,
        elements_datatypes: ["txt"],
        elements_deleted: 0,
        elements_states: {},
        collection_type: "list",
        populated_state: "ok",
        populated_state_message: "",
        collection_id: `DC_ID_${id}`,
        name: `collection ${id}`,
        deleted: false,
        contents_url: "",
        hid: 1,
        history_content_type: "dataset_collection",
        history_id: "1",
        model_class: "HistoryDatasetCollectionAssociation",
        tags: [],
        visible: true,
        create_time: "2021-05-25T14:00:00.000Z",
        update_time: "2021-05-25T14:00:00.000Z",
        type_id: "dataset_collection",
        url: "",
        type: "collection",
        store_times_summary: null,
        ...overrides,
    };
}
