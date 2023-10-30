import { fetcher } from "@/api/schema";
import Filtering, { contains, equals, expandNameTagWithQuotes, toBool } from "@/utils/filtering";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString, rethrowSimple } from "@/utils/simple-error";
import type { Router } from "vue-router";

/**
 * Api endpoint fetchers
 */
const createVisualization = fetcher.path("/api/visualizations").method("post").create();
const getVisualization = fetcher.path("/api/visualizations/{visualization_id}").method("get").create();
const getDetailedVisualizations = fetcher.path("/api/visualizations/detailed").method("get").create();
const updateVisualization = fetcher.path("/api/visualizations/{visualization_id}").method("put").create();
const updateTags = fetcher.path("/api/tags").method("put").create();

/**
 * Local types
 */
type SortKeyLiteral =  "create_time" | "title" | "update_time" |;

/**
 * Request and return data from server
 */
async function getData(offset: number, limit: number, search: string, sort_by: SortKeyLiteral, sort_desc: boolean) {
    const { data, headers } = await getDetailedVisualizations({
        limit,
        offset,
        search,
        sort_by,
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
        operations: [
            {
                title: "Open",
                icon: "eye",
                handler: (data: Record<string, unknown>) => {
                    window.location.href = withPrefix(`/plugins/visualizations/${data.type}/saved?id=${data.id}`);
                },
            },
            {
                title: "Edit Attributes",
                icon: "edit",
                handler: (data: Record<string, unknown>, router: Router) => {
                    router.push(`/visualizations/edit?id=${data.id}`);
                },
            },
            {
                title: "Copy",
                icon: "copy",
                handler: async (data: Record<string, unknown>) => {
                    try {
                        const copyResponse = await getVisualization({ visualization_id: data.id });
                        const copyViz = copyResponse.data;
                        const newViz = {
                            title: `Copy of '${copyViz.title}'`,
                            type: copyViz.type,
                            config: copyViz.config,
                        };
                        await createVisualization(newViz);
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
                handler: (data: Record<string, unknown>, router: Router) => {
                    router.push(`/visualizations/sharing?id=${data.id}`);
                },
            },
            {
                title: "Delete",
                icon: "trash",
                handler: async (data: Record<string, unknown>) => {
                    try {
                        await updateVisualization({ visualization_id: data.id, deleted: true });
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
        handler: async (data: Record<string, unknown>) => {
            const tagPayload = {
                item_id: data.id,
                item_class: "Visualization",
                item_tags: data.tags,
            };
            try {
                await updateTags(tagPayload);
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
const validFilters = {
    title: { placeholder: "title", type: String, handler: contains("title"), menuItem: true },
    slug: { handler: contains("slug"), menuItem: false },
    tag: {
        placeholder: "tag(s)",
        type: "MultiTags",
        handler: contains("tag", "tag", expandNameTagWithQuotes),
        menuItem: true,
    },
    user: { placeholder: "user name", type: String, handler: contains("user"), menuItem: true },
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
