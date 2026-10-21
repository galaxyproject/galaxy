import type { Decorator } from "@storybook/vue3-vite";
import { getFakeCollectionSummary } from "@tests/test-data/collections";
import { getFakeDatasetDetails, getFakeDatasetSummary } from "@tests/test-data/datasets";
import { getFakeWorkflowSummary } from "@tests/test-data/workflows";
import { HttpResponse } from "msw";
import { h, onBeforeUnmount } from "vue";

import type { HDCADetailed } from "@/api";
import { http } from "@/api/client/__mocks__/http";
import { CURRENT_HISTORY, HISTORY_DATASETS } from "@/components/SelectionField/test_fixtures";
import { useEventStore } from "@/stores/eventStore";

export const MARKDOWN_DATASET = getFakeDatasetSummary({
    id: "f2db41e1fa331b3e",
    hid: 3,
    name: HISTORY_DATASETS[2].name,
    extension: "tabular",
    history_id: CURRENT_HISTORY.id,
});

export const MARKDOWN_COLLECTION = getFakeCollectionSummary({
    id: "1cd8e2f6b131e891",
    collection_id: "3ec56a0f2d421681",
    hid: 4,
    name: "Gene counts by sample",
    history_id: CURRENT_HISTORY.id,
    collection_type: "list",
    element_count: 1,
    elements_datatypes: ["tabular"],
    contents_url: "/api/dataset_collections/1cd8e2f6b131e891/contents/3ec56a0f2d421681",
    url: `/api/histories/${CURRENT_HISTORY.id}/contents/dataset_collections/1cd8e2f6b131e891`,
});

export const MARKDOWN_COLLECTION_DETAILS: HDCADetailed = {
    ...MARKDOWN_COLLECTION,
    elements: [
        {
            id: "f29be6c7a4450283",
            model_class: "DatasetCollectionElement",
            element_identifier: "sample",
            element_index: 0,
            element_type: "hda",
            object: getFakeDatasetDetails({
                ...MARKDOWN_DATASET,
                type: "file",
                data_type: "galaxy.datatypes.tabular.Tabular",
            }),
        },
    ],
};

/** A workflow is draggable elsewhere in Galaxy, but isn't a history item for a page. */
export const MARKDOWN_WORKFLOW = getFakeWorkflowSummary({
    id: "425b519060cbe8f4",
    latest_workflow_id: "206be113aa3d8212",
    latest_workflow_uuid: "bb09467e-7cb6-45a3-a99a-760af5fd0011",
    name: "RNA-seq analysis",
});

/** Own only this story's drag fields; restore a preceding drag without clearing other event state. */
export const withMarkdownDrag: Decorator = (story) => ({
    setup() {
        const store = useEventStore();
        const previous = store.getDragData();
        const multiple = store.multipleDragData;
        store.clearDragData();
        onBeforeUnmount(() => {
            if (previous) {
                store.setDragData(previous, multiple);
            } else {
                store.clearDragData();
                store.multipleDragData = multiple;
            }
        });
        return () => h(story());
    },
});

/** Normal toolbox browsing, for a history with data but no executions or published objects. */
export const markdownToolboxHandlers = {
    plugins: http.get("/api/plugins", ({ response }) => response(200).json([])),
    historyContents: http.get("/api/histories/{history_id}/contents", ({ params, request, response }) => {
        if (params.history_id === CURRENT_HISTORY.id) {
            const items =
                new URL(request.url).searchParams.get("type") === "dataset_collection"
                    ? [MARKDOWN_COLLECTION]
                    : [MARKDOWN_DATASET, MARKDOWN_COLLECTION];
            return response(200).json(items);
        }
    }),
    // openapi-msw maps {type}s to :types, losing the typed type parameter. Match
    // this fixed collection route directly; the response still uses HDCADetailed.
    collectionContents: http.untyped.get(
        "/api/histories/:history_id/contents/dataset_collections/:id",
        ({ params }) => {
            if (params.history_id === CURRENT_HISTORY.id && params.id === MARKDOWN_COLLECTION.id) {
                return HttpResponse.json(MARKDOWN_COLLECTION_DETAILS);
            }
        },
    ),
    libraries: http.get("/api/libraries", ({ response }) => response(200).json([])),
    jobs: http.get("/api/jobs", ({ response }) => response(200).json([])),
    invocations: http.get("/api/invocations", ({ response }) => response(200).json([])),
    workflows: http.get("/api/workflows", ({ response }) => response(200).json([])),
    publishedHistories: http.get("/api/histories/published", ({ response }) => response(200).json([])),
};
