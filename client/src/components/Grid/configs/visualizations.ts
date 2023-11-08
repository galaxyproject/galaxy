import axios from "axios";
import type Router from "vue-router";

import { fetcher } from "@/api/schema";
import Filtering, { contains, equals, expandNameTag, toBool, type ValidFilter } from "@/utils/filtering";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString, rethrowSimple } from "@/utils/simple-error";

/**
 * Api endpoint handlers
 */
const getVisualizations = fetcher.path("/api/visualizations").method("get").create();
const updateTags = fetcher.path("/api/tags").method("put").create();

/**
 * Local types
 */
type SortKeyLiteral = "create_time" | "title" | "update_time" | "username" | undefined;
type VisualizationEntry = Record<string, unknown>;

/**
 * Request and return data from server
 */
async function getData(offset: number, limit: number, search: string, sort_by: string, sort_desc: boolean) {
    const { data, headers } = await getVisualizations({
        limit,
        offset,
        search,
        sort_by: sort_by as SortKeyLiteral,
        sort_desc,
    });
    const totalMatches = parseInt(headers.get("total_matches") ?? "0");
    return [data, totalMatches];
}

/**
 * Actions are grid-wide operations
 */
const actions = [
    {
        title: "Create",
        icon: "plus",
        handler: (router: Router) => {
            router.push(`/visualizations`);
        },
    },
];

/**
 * Declare columns to be displayed
 */
const fields = [
    {
        title: "Title",
        key: "title",
        type: "operations",
        width: "40%",
        condition: (data: VisualizationEntry) => !data.deleted,
        operations: [
            {
                title: "Open",
                icon: "eye",
                condition: (data: VisualizationEntry) => !data.deleted,
                handler: (data: VisualizationEntry) => {
                    window.location.href = withPrefix(`/plugins/visualizations/${data.type}/saved?id=${data.id}`);
                },
            },
            {
                title: "Edit Attributes",
                icon: "edit",
                condition: (data: VisualizationEntry) => !data.deleted,
                handler: (data: VisualizationEntry, router: Router) => {
                    router.push(`/visualizations/edit?id=${data.id}`);
                },
            },
            {
                title: "Copy",
                icon: "copy",
                condition: (data: VisualizationEntry) => !data.deleted,
                handler: async (data: VisualizationEntry) => {
                    try {
                        const copyResponse = await axios.get(withPrefix(`/api/visualizations/${data.id}`));
                        const copyViz = copyResponse.data;
                        const newViz = {
                            title: `Copy of '${copyViz.title}'`,
                            type: copyViz.type,
                            config: copyViz.config,
                        };
                        await axios.post(withPrefix(`/api/visualizations`), newViz);
                        return {
                            status: "success",
                            message: `'${data.title}' has been copied.`,
                        };
                    } catch (e) {
                        return {
                            status: "danger",
                            message: `Failed to copy '${data.title}': ${errorMessageAsString(e)}.`,
                        };
                    }
                },
            },
            {
                title: "Share and Publish",
                icon: "share-alt",
                condition: (data: VisualizationEntry) => !data.deleted,
                handler: (data: VisualizationEntry, router: Router) => {
                    router.push(`/visualizations/sharing?id=${data.id}`);
                },
            },
            {
                title: "Delete",
                icon: "trash",
                condition: (data: VisualizationEntry) => !data.deleted,
                handler: async (data: VisualizationEntry) => {
                    try {
                        await axios.put(`/api/visualizations/${data.id}`, { deleted: true });
                        return {
                            status: "success",
                            message: `'${data.title}' has been deleted.`,
                        };
                    } catch (e) {
                        return {
                            status: "danger",
                            message: `Failed to delete '${data.title}': ${errorMessageAsString(e)}.`,
                        };
                    }
                },
            },
            {
                title: "Restore",
                icon: "trash-restore",
                condition: (data: VisualizationEntry) => data.deleted,
                handler: async (data: VisualizationEntry) => {
                    try {
                        await axios.put(`/api/visualizations/${data.id}`, { deleted: false });
                        return {
                            status: "success",
                            message: `'${data.title}' has been restored.`,
                        };
                    } catch (e) {
                        return {
                            status: "danger",
                            message: `Failed to restore '${data.title}': ${errorMessageAsString(e)}.`,
                        };
                    }
                },
            },
        ],
    },
    {
        key: "type",
        title: "Type",
        type: "text",
    },
    {
        key: "tags",
        title: "Tags",
        type: "tags",
        handler: async (data: VisualizationEntry) => {
            try {
                await updateTags({
                    item_id: data.id as string,
                    item_class: "Visualization",
                    item_tags: data.tags as Array<string>,
                });
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
        title: "Shared",
        type: "sharing",
    },
];

/**
 * Declare filter options
 */
const validFilters: Record<string, ValidFilter<string | boolean | undefined>> = {
    title: { placeholder: "title", type: String, handler: contains("title"), menuItem: true },
    slug: { handler: contains("slug"), menuItem: false },
    tag: {
        placeholder: "tag(s)",
        type: "MultiTags",
        handler: contains("tag", "tag", expandNameTag),
        menuItem: true,
    },
    published: {
        placeholder: "Filter on published visualizations",
        type: Boolean,
        boolType: "is",
        handler: equals("published", "published", toBool),
        menuItem: true,
    },
    importable: {
        placeholder: "Filter on importable visualizations",
        type: Boolean,
        boolType: "is",
        handler: equals("importable", "importable", toBool),
        menuItem: true,
    },
    deleted: {
        placeholder: "Filter on deleted visualizations",
        type: Boolean,
        boolType: "is",
        handler: equals("deleted", "deleted", toBool),
        menuItem: true,
    },
};

/**
 * Grid configuration
 */
export const VisualizationsGrid = {
    actions: actions,
    fields: fields,
    filtering: new Filtering(validFilters, undefined, false, false),
    getData: getData,
    item: "visualization",
    plural: "Visualizations",
    sortBy: "update_time",
    sortDesc: true,
    sortKeys: ["create_time", "title", "update_time"],
    title: "Saved Visualizations",
};
