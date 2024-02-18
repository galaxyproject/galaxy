import { faEdit, faEye, faPlus, faShareAlt, faTrash } from "@fortawesome/free-solid-svg-icons";
import { useEventBus } from "@vueuse/core";

import { fetcher } from "@/api/schema";
import { getGalaxyInstance } from "@/app";
import Filtering, { contains, equals, toBool, type ValidFilter } from "@/utils/filtering";
import { errorMessageAsString, rethrowSimple } from "@/utils/simple-error";

import type { ActionArray, FieldArray, GridConfig } from "./types";

const { emit } = useEventBus<string>("grid-router-push");

/**
 * Api endpoint handlers
 */
const getPages = fetcher.path("/api/pages").method("get").create();
const deletePage = fetcher.path("/api/pages/{id}").method("delete").create();

/**
 * Local types
 */
type SortKeyLiteral = "create_time" | "title" | "update_time" | "username" | undefined;
type PageEntry = Record<string, unknown>;

/**
 * Request and return data from server
 */
async function getData(offset: number, limit: number, search: string, sort_by: string, sort_desc: boolean) {
    // TODO: Avoid using Galaxy instance to identify current user
    const Galaxy = getGalaxyInstance();
    const userId = !Galaxy.isAnonymous && Galaxy.user.id;
    if (!userId) {
        rethrowSimple("Please login to access this page.");
    }
    const { data, headers } = await getPages({
        limit,
        offset,
        search,
        sort_by: sort_by as SortKeyLiteral,
        sort_desc,
        show_published: false,
        user_id: userId,
    });
    const totalMatches = parseInt(headers.get("total_matches") ?? "0");
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
                icon: faEdit,
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
                    try {
                        await deletePage({ id: String(data.id) });
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
        placeholder: "Filter on published pages",
        type: Boolean,
        boolType: "is",
        handler: equals("published", "published", toBool),
        menuItem: true,
    },
    importable: {
        placeholder: "Filter on importable pages",
        type: Boolean,
        boolType: "is",
        handler: equals("importable", "importable", toBool),
        menuItem: true,
    },
    deleted: {
        placeholder: "Filter on deleted pages",
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
