import {
    faExchangeAlt,
    faEye,
    faPlus,
    faShareAlt,
    faSignature,
    faTrash,
    faTrashRestore,
    faUsers,
} from "@fortawesome/free-solid-svg-icons";
import { useEventBus } from "@vueuse/core";

import { deleteHistories, deleteHistory, historiesFetcher, undeleteHistories, undeleteHistory } from "@/api/histories";
import { updateTags } from "@/api/tags";
import { useHistoryStore } from "@/stores/historyStore";
import Filtering, { contains, equals, expandNameTag, toBool, type ValidFilter } from "@/utils/filtering";
import _l from "@/utils/localization";
import { errorMessageAsString, rethrowSimple } from "@/utils/simple-error";

import type { ActionArray, BatchOperationArray, FieldArray, GridConfig } from "./types";

const { emit } = useEventBus<string>("grid-router-push");

/**
 * Local types
 */
type HistoryEntry = Record<string, unknown>;
type SortKeyLiteral = "create_time" | "name" | "update_time" | undefined;

/**
 * Request and return data from server
 */
async function getData(offset: number, limit: number, search: string, sort_by: string, sort_desc: boolean) {
    const { data, headers } = await historiesFetcher({
        view: "summary",
        keys: "create_time",
        limit,
        offset,
        search,
        sort_by: sort_by as SortKeyLiteral,
        sort_desc,
        show_own: true,
        show_published: false,
        show_shared: false,
    });
    const totalMatches = parseInt(headers.get("total_matches") ?? "0");
    return [data, totalMatches];
}

/**
 * Actions are grid-wide operations
 */
const actions: ActionArray = [
    {
        title: "Import New History",
        icon: faPlus,
        handler: () => {
            emit("/histories/import");
        },
    },
];

// Batch operation
const batch: BatchOperationArray = [
    {
        title: "Delete",
        icon: faTrash,
        condition: (data: Array<HistoryEntry>) => !data.some((x) => x.deleted),
        handler: async (data: Array<HistoryEntry>) => {
            if (confirm(_l(`Are you sure that you want to delete the selected histories?`))) {
                try {
                    const historyIds = data.map((x) => String(x.id));
                    await deleteHistories({ ids: historyIds });
                    return {
                        status: "success",
                        message: `Deleted ${data.length} histories.`,
                    };
                } catch (e) {
                    return {
                        status: "danger",
                        message: `Failed to delete histories: ${errorMessageAsString(e)}`,
                    };
                }
            }
        },
    },
    {
        title: "Restore",
        icon: faTrashRestore,
        condition: (data: Array<HistoryEntry>) => !data.some((x) => !x.deleted || x.purged),
        handler: async (data: Array<HistoryEntry>) => {
            if (confirm(_l(`Are you sure that you want to restore the selected histories?`))) {
                try {
                    const historyIds = data.map((x) => String(x.id));
                    await undeleteHistories({ ids: historyIds });
                    return {
                        status: "success",
                        message: `Restored ${data.length} histories.`,
                    };
                } catch (e) {
                    return {
                        status: "danger",
                        message: `Failed to restore histories: ${errorMessageAsString(e)}`,
                    };
                }
            }
        },
    },
    {
        title: "Purge",
        icon: faTrash,
        condition: (data: Array<HistoryEntry>) => !data.some((x) => x.purged),
        handler: async (data: Array<HistoryEntry>) => {
            if (confirm(_l(`Are you sure that you want to permanently delete the selected histories?`))) {
                try {
                    const historyIds = data.map((x) => String(x.id));
                    await deleteHistories({ ids: historyIds, purge: true });
                    return {
                        status: "success",
                        message: `Purged ${data.length} histories.`,
                    };
                } catch (e) {
                    return {
                        status: "danger",
                        message: `Failed to delete histories: ${errorMessageAsString(e)}`,
                    };
                }
            }
        },
    },
];

/**
 * Declare columns to be displayed
 */
const fields: FieldArray = [
    {
        key: "name",
        title: "Name",
        type: "operations",
        operations: [
            {
                title: "Switch",
                icon: faExchangeAlt,
                handler: (data: HistoryEntry) => {
                    const historyStore = useHistoryStore();
                    historyStore.setCurrentHistory(String(data.id));
                },
            },
            {
                title: "View",
                icon: faEye,
                handler: (data: HistoryEntry) => {
                    emit(`/histories/view?id=${data.id}`);
                },
            },
            {
                title: "Rename",
                icon: faSignature,
                condition: (data: HistoryEntry) => !data.deleted,
                handler: (data: HistoryEntry) => {
                    emit(`/histories/rename?id=${data.id}`);
                },
            },
            {
                title: "Share and Publish",
                icon: faShareAlt,
                condition: (data: HistoryEntry) => !data.deleted,
                handler: (data: HistoryEntry) => {
                    emit(`/histories/sharing?id=${data.id}`);
                },
            },
            {
                title: "Change Permissions",
                icon: faUsers,
                condition: (data: HistoryEntry) => !data.deleted,
                handler: (data: HistoryEntry) => {
                    emit(`/histories/permissions?id=${data.id}`);
                },
            },
            {
                title: "Delete",
                icon: faTrash,
                condition: (data: HistoryEntry) => !data.deleted,
                handler: async (data: HistoryEntry) => {
                    if (confirm(_l("Are you sure that you want to delete this history?"))) {
                        try {
                            await deleteHistory({ history_id: String(data.id) });
                            return {
                                status: "success",
                                message: `'${data.name}' has been deleted.`,
                            };
                        } catch (e) {
                            return {
                                status: "danger",
                                message: `Failed to delete '${data.name}': ${errorMessageAsString(e)}`,
                            };
                        }
                    }
                },
            },
            {
                title: "Delete Permanently",
                icon: faTrash,
                condition: (data: HistoryEntry) => !data.purged,
                handler: async (data: HistoryEntry) => {
                    if (confirm(_l("Are you sure that you want to permanently delete this history?"))) {
                        try {
                            await deleteHistory({ history_id: String(data.id), purge: true });
                            return {
                                status: "success",
                                message: `'${data.name}' has been permanently deleted.`,
                            };
                        } catch (e) {
                            return {
                                status: "danger",
                                message: `Failed to permanently delete '${data.name}': ${errorMessageAsString(e)}`,
                            };
                        }
                    }
                },
            },
            {
                title: "Restore",
                icon: faTrashRestore,
                condition: (data: HistoryEntry) => !!data.deleted && !data.purged,
                handler: async (data: HistoryEntry) => {
                    try {
                        await undeleteHistory({ history_id: String(data.id) });
                        return {
                            status: "success",
                            message: `'${data.name}' has been restored.`,
                        };
                    } catch (e) {
                        return {
                            status: "danger",
                            message: `Failed to restore '${data.name}': ${errorMessageAsString(e)}`,
                        };
                    }
                },
            },
        ],
    },
    {
        key: "count",
        title: "Items",
        type: "text",
    },
    {
        key: "id",
        title: "Size",
        type: "datasets",
    },
    {
        key: "tags",
        title: "Tags",
        type: "tags",
        handler: async (data: HistoryEntry) => {
            try {
                await updateTags(data.id as string, "History", data.tags as Array<string>);
            } catch (e) {
                rethrowSimple(e);
            }
        },
    },
    {
        key: "create_time",
        title: "Created",
        type: "date",
    },
    {
        key: "update_time",
        title: "Updated",
        type: "date",
    },
    {
        key: "sharing",
        title: "Status",
        type: "sharing",
    },
];

/**
 * Declare filter options
 */
const validFilters: Record<string, ValidFilter<string | boolean | undefined>> = {
    name: { placeholder: "name", type: String, handler: contains("name"), menuItem: true },
    tag: {
        placeholder: "tag(s)",
        type: "MultiTags",
        handler: contains("tag", "tag", expandNameTag),
        menuItem: true,
    },
    published: {
        placeholder: "Published",
        type: Boolean,
        boolType: "is",
        handler: equals("published", "published", toBool),
        menuItem: true,
    },
    importable: {
        placeholder: "Importable",
        type: Boolean,
        boolType: "is",
        handler: equals("importable", "importable", toBool),
        menuItem: true,
    },
    deleted: {
        placeholder: "Deleted",
        type: Boolean,
        boolType: "is",
        handler: equals("deleted", "deleted", toBool),
        menuItem: true,
    },
    purged: {
        placeholder: "Purged entries",
        type: Boolean,
        boolType: "is",
        handler: equals("purged", "purged", toBool),
        menuItem: true,
    },
};

/**
 * Grid configuration
 */
const gridConfig: GridConfig = {
    id: "histories-grid",
    actions: actions,
    fields: fields,
    filtering: new Filtering(validFilters, undefined, false, false),
    getData: getData,
    batch: batch,
    plural: "Histories",
    sortBy: "update_time",
    sortDesc: true,
    sortKeys: ["create_time", "name", "update_time"],
    title: "Histories",
};

export default gridConfig;
