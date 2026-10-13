import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";

import { configurationHandler, http } from "@/api/client/__mocks__/http";
import { selectableObjectStores } from "@/components/ObjectStore/test_fixtures";

import {
    DELETED_DATASET,
    HIDDEN_DATASET,
    HISTORY,
    PURGED_DATASET,
    READS_COLLECTION,
    selectionOf,
    VISIBLE_DATASET,
} from "./test_fixtures";

import SelectionOperations from "./SelectionOperations.vue";

/**
 * The "Selection" menu above a history's items, once some are selected, on a Galaxy that runs
 * background tasks, so the data type and storage operations are offered.
 */
const meta = {
    title: "History/CurrentHistory/HistoryOperations/SelectionOperations",
    component: SelectionOperations,
    decorators: [withCurrentUser()],
    args: {
        history: HISTORY,
        filterText: "",
        contentSelection: selectionOf(VISIBLE_DATASET),
        selectionSize: 1,
        isQuerySelection: false,
        isMultiViewItem: false,
        totalItemsInQuery: HISTORY.count,
    },
    argTypes: { contentSelection: { control: false } },
    parameters: {
        msw: {
            handlers: {
                configuration: configurationHandler({ enable_celery_tasks: true }),
                objectStores: selectableObjectStores(),
                // The Database/Build dialog lists them when it opens.
                genomes: http.get("/api/genomes", ({ response }) => response(200).json([])),
            },
        },
    },
} satisfies Meta<typeof SelectionOperations>;

export default meta;
type Story = StoryObj<typeof meta>;

/** One visible dataset selected under the default filter. */
export const DatasetSelected: Story = {};

/** Showing hidden items only, with a hidden dataset selected: it can be unhidden. */
export const HiddenSelected: Story = {
    args: { filterText: "visible:false", contentSelection: selectionOf(HIDDEN_DATASET) },
};

/** Showing visible and hidden items, with one of each selected: both hide and unhide apply. */
export const VisibleAndHiddenSelected: Story = {
    args: {
        filterText: "visible:any",
        contentSelection: selectionOf(VISIBLE_DATASET, HIDDEN_DATASET),
        selectionSize: 2,
    },
};

/** Showing deleted items only, with a deleted dataset selected: it can be undeleted. */
export const DeletedSelected: Story = {
    args: { filterText: "deleted:true", contentSelection: selectionOf(DELETED_DATASET) },
};

/** Showing active and deleted items, with one of each selected: both delete and undelete apply. */
export const ActiveAndDeletedSelected: Story = {
    args: {
        filterText: "deleted:any",
        contentSelection: selectionOf(VISIBLE_DATASET, DELETED_DATASET),
        selectionSize: 2,
    },
};

/** Showing active and deleted items, with an active collection selected: it can be deleted, not undeleted. */
export const ActiveCollectionSelected: Story = {
    args: { filterText: "deleted:any", contentSelection: selectionOf(READS_COLLECTION) },
};

/** Showing deleted items only, with a purged dataset selected: it can't be undeleted or purged again. */
export const PurgedSelected: Story = {
    args: { filterText: "deleted:true", contentSelection: selectionOf(PURGED_DATASET) },
};

/** Every item the filter matches is selected, so the menu offers a list built from all of them. */
export const WholeQuerySelected: Story = {
    args: { history: { ...HISTORY, count: 105 }, selectionSize: 105, totalItemsInQuery: 105, isQuerySelection: true },
};

/** A Galaxy without background tasks: no data type or storage operations. */
export const WithoutCelery: Story = {
    parameters: { msw: { handlers: { configuration: configurationHandler({ enable_celery_tasks: false }) } } },
};
