import { faEye } from "@fortawesome/free-solid-svg-icons";
import { useEventBus } from "@vueuse/core";

import { GalaxyApi } from "@/api";
import { updateTags } from "@/api/tags";
import Filtering, { contains, expandNameTag, type ValidFilter } from "@/utils/filtering";
import _l from "@/utils/localization";
import { rethrowSimple } from "@/utils/simple-error";

import { type FieldArray, type GridConfig } from "./types";

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
    const { response, data, error } = await GalaxyApi().GET("/api/histories", {
        params: {
            query: {
                view: "summary",
                keys: "username,create_time",
                limit,
                offset,
                search,
                sort_by: sort_by as SortKeyLiteral,
                sort_desc,
                show_own: false,
                show_published: false,
                show_shared: true,
                show_archived: true,
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
        key: "name",
        title: "Name",
        type: "operations",
        operations: [
            {
                title: "View",
                icon: faEye,
                condition: (data: HistoryEntry) => !data.deleted,
                handler: (data: HistoryEntry) => {
                    emit(`/histories/view?id=${data.id}`);
                },
            },
        ],
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
        disabled: true,
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
        key: "username",
        title: "Username",
        type: "text",
    },
];

/**
 * Declare filter options
 */
const validFilters: Record<string, ValidFilter<string | boolean | undefined>> = {
    name: { placeholder: "name", type: String, handler: contains("name"), menuItem: true },
    user: { placeholder: "user", type: String, handler: contains("username"), menuItem: true },
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
    id: "histories-shared-grid",
    fields: fields,
    filtering: new Filtering(validFilters, undefined, false, false),
    getData: getData,
    plural: "Histories",
    sortBy: "update_time",
    sortDesc: true,
    sortKeys: ["create_time", "name", "update_time", "username"],
    title: "Shared Histories",
};

export default gridConfig;
