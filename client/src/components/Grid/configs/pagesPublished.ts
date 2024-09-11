import { faEye, faPlus } from "@fortawesome/free-solid-svg-icons";
import { useEventBus } from "@vueuse/core";

import { GalaxyApi } from "@/api";
import Filtering, { contains, type ValidFilter } from "@/utils/filtering";
import { rethrowSimple } from "@/utils/simple-error";

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
        key: "username",
        title: "Owner",
        type: "text",
    },
];

/**
 * Declare filter options
 */
const validFilters: Record<string, ValidFilter<string | boolean | undefined>> = {
    title: { placeholder: "title", type: String, handler: contains("title"), menuItem: true },
    slug: { handler: contains("slug"), menuItem: false },
};

/**
 * Grid configuration
 */
const gridConfig: GridConfig = {
    id: "pages-published-grid",
    actions: actions,
    fields: fields,
    filtering: new Filtering(validFilters, undefined, false, false),
    getData: getData,
    plural: "Pages",
    sortBy: "update_time",
    sortDesc: true,
    sortKeys: ["create_time", "title", "update_time"],
    title: "Published Pages",
};

export default gridConfig;
