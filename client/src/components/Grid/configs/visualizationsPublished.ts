import { faEye } from "@fortawesome/free-solid-svg-icons";

import { GalaxyApi } from "@/api";
import Filtering, { contains, expandNameTag, type ValidFilter } from "@/utils/filtering";
import { withPrefix } from "@/utils/redirect";
import { rethrowSimple } from "@/utils/simple-error";

import { type FieldArray, type GridConfig } from "./types";

/**
 * Local types
 */
type SortKeyLiteral = "create_time" | "title" | "update_time" | "username" | undefined;
type VisualizationEntry = Record<string, unknown>;

/**
 * Request and return data from server
 */
async function getData(offset: number, limit: number, search: string, sort_by: string, sort_desc: boolean) {
    const { response, data, error } = await GalaxyApi().GET("/api/visualizations", {
        params: {
            query: {
                limit,
                offset,
                search,
                sort_by: sort_by as SortKeyLiteral,
                sort_desc,
                show_own: false,
                show_published: true,
                show_shared: true,
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
                handler: (data: VisualizationEntry) => {
                    if (data.type === "trackster") {
                        window.location.href = withPrefix(`/visualization/${data.type}?id=${data.id}`);
                    } else {
                        window.location.href = withPrefix(`/plugins/visualizations/${data.type}/saved?id=${data.id}`);
                    }
                },
            },
        ],
    },
    {
        key: "annotation",
        title: "Annotation",
        type: "text",
    },
    {
        key: "username",
        title: "Owner",
        type: "text",
    },
    {
        key: "tags",
        title: "Tags",
        type: "tags",
        disabled: true,
    },
    {
        key: "update_time",
        title: "Updated",
        type: "date",
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
};

/**
 * Grid configuration
 */
const gridConfig: GridConfig = {
    id: "visualizations-published-grid",
    fields: fields,
    filtering: new Filtering(validFilters, undefined, false, false),
    getData: getData,
    plural: "Visualizations",
    sortBy: "update_time",
    sortDesc: true,
    sortKeys: ["create_time", "title", "update_time"],
    title: "Published Visualizations",
};

export default gridConfig;
