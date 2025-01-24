import { faEdit, faEye, faPen, faPlus, faShareAlt, faTrash, faTrashRestore } from "@fortawesome/free-solid-svg-icons";
import { useEventBus } from "@vueuse/core";

import { GalaxyApi } from "@/api";
import Filtering, { contains, equals, toBool, type ValidFilter } from "@/utils/filtering";
import _l from "@/utils/localization";
import { errorMessageAsString, rethrowSimple } from "@/utils/simple-error";

import { type ActionArray, type FieldArray, type GridConfig } from "./types";

const { emit } = useEventBus<string>("grid-router-push");

/**
 * Local types
 */
type SortKeyLiteral = "create_time" | "title" | "update_time" | "username" | undefined;
type PageEntry = Record<string, unknown>;

/**
 * Request and return data from server
 */
async function getData(offset: number, limit: number, search: string, sort_by: string, sort_desc: boolean) {
    const { response, data, error } = await GalaxyApi().GET("/api/pages", {
        params: {
            query: {
                limit,
                offset,
                search,
                sort_by: sort_by as SortKeyLiteral,
                sort_desc,
                show_published: false,
                show_own: true,
                show_shared: false,
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    const totalMatches = parseInt(response.headers.get("total_matches") ?? "0");
    return [data, totalMatches];
}

/**
 * Actions are grid-wide operations
 */
const actions: ActionArray = [
    {
        title: "Create",
        icon: faPlus,
        handler: () => {
            emit("/pages/create");
        },
    },
];

/**
 * Declare columns to be displayed
 */
const fields: FieldArray = [
    {
        title: "Title",
        key: "title",
        type: "operations",
        width: 40,
        operations: [
            {
                title: "View",
                icon: faEye,
                handler: (data: PageEntry) => {
                    emit(`/published/page?id=${data.id}`);
                },
            },
            {
                title: "Edit Attributes",
                icon: faEdit,
                condition: (data: PageEntry) => !data.deleted,
                handler: (data: PageEntry) => {
                    emit(`/pages/edit?id=${data.id}`);
                },
            },
            {
                title: "Edit Content",
                icon: faPen,
                condition: (data: PageEntry) => !data.deleted,
                handler: (data: PageEntry) => {
                    emit(`/pages/editor?id=${data.id}`);
                },
            },
            {
                title: "Share and Publish",
                icon: faShareAlt,
                condition: (data: PageEntry) => !data.deleted,
                handler: (data: PageEntry) => {
                    emit(`/pages/sharing?id=${data.id}`);
                },
            },
            {
                title: "Delete",
                icon: faTrash,
                condition: (data: PageEntry) => !data.deleted,
                handler: async (data: PageEntry) => {
                    if (confirm(_l(`Are you sure that you want to delete the selected page?`))) {
                        const { error } = await GalaxyApi().DELETE("/api/pages/{id}", {
                            params: {
                                path: { id: String(data.id) },
                            },
                        });

                        if (error) {
                            return {
                                status: "danger",
                                message: `Failed to delete '${data.title}': ${errorMessageAsString(error)}.`,
                            };
                        }

                        return {
                            status: "success",
                            message: `'${data.title}' has been deleted.`,
                        };
                    }
                },
            },
            {
                title: "Restore",
                icon: faTrashRestore,
                condition: (data: PageEntry) => !!data.deleted,
                handler: async (data: PageEntry) => {
                    if (confirm(_l(`Are you sure that you want to restore the selected page?`))) {
                        const { error } = await GalaxyApi().PUT("/api/pages/{id}/undelete", {
                            params: {
                                path: { id: String(data.id) },
                            },
                        });

                        if (error) {
                            return {
                                status: "danger",
                                message: `Failed to restore '${data.title}': ${errorMessageAsString(error)}.`,
                            };
                        }

                        return {
                            status: "success",
                            message: `'${data.title}' has been restored.`,
                        };
                    }
                },
            },
        ],
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
    title: { placeholder: "title", type: String, handler: contains("title"), menuItem: true },
    slug: { handler: contains("slug"), menuItem: false },
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
};

/**
 * Grid configuration
 */
const gridConfig: GridConfig = {
    id: "pages-grid",
    actions: actions,
    fields: fields,
    filtering: new Filtering(validFilters, undefined, false, false),
    getData: getData,
    plural: "Pages",
    sortBy: "update_time",
    sortDesc: true,
    sortKeys: ["create_time", "title", "update_time"],
    title: "Saved Pages",
};

export default gridConfig;
