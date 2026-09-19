import { faEye } from "@fortawesome/free-solid-svg-icons";
import { useEventBus } from "@vueuse/core";

import { loadVisualizations, type VisualizationSortByLiteral } from "@/api/visualizations";
import Filtering, { contains, expandNameTag, type ValidFilter } from "@/utils/filtering";

import type { FieldArray, GridConfig } from "./types";

const { emit } = useEventBus<string>("grid-router-push");

/**
 * Local types
 */
type VisualizationEntry = Record<string, unknown>;

/**
 * Request and return data from server
 */
async function getData(offset: number, limit: number, search: string, sort_by: string, sort_desc: boolean) {
    const { data, totalMatches } = await loadVisualizations({
        limit,
        offset,
        search,
        sortBy: sort_by as VisualizationSortByLiteral,
        sortDesc: sort_desc,
        showOwn: false,
        showPublished: true,
        showShared: true,
    });

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
                    emit(`/visualizations/display?visualization=${data.type}&visualization_id=${data.id}`, {
                        title: data.title,
                    });
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
        type: "link",
        handler: (data: VisualizationEntry) => {
            emit(`/visualizations/list_published?f-username=${data.username}`);
        },
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
    user: { placeholder: "user", type: String, handler: contains("username"), menuItem: true },
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
