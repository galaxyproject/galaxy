import { faCopy, faEdit, faExchangeAlt, faEye, faPlus, faShareAlt, faSignature, faTrash, faTrashRestore } from "@fortawesome/free-solid-svg-icons";
import { useEventBus } from "@vueuse/core";

import { deleteForm, undeleteForm } from "@/api/forms";
import { historiesQuery } from "@/api/histories";
import Filtering, { contains, equals, toBool, type ValidFilter } from "@/utils/filtering";
import _l from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import type { ActionArray, FieldArray, GridConfig } from "./types";

const { emit } = useEventBus<string>("grid-router-push");

/**
 * Local types
 */
type FormEntry = Record<string, unknown>;
type SortKeyLiteral = "create_time" | "name" | "update_time" | undefined;

/**
 * Request and return data from server
 */
async function getData(offset: number, limit: number, search: string, sort_by: string, sort_desc: boolean) {
    const { data, headers } = await historiesQuery({
        limit,
        offset,
        search,
        sort_by: sort_by as SortKeyLiteral,
        sort_desc,
        show_published: false,
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
            emit("/admin/form/create_form");
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
                condition: (data: FormEntry) => !data.deleted,
                handler: (data: FormEntry) => {
                    emit(`/histories/view?id=${data.id}`);
                },
            },
            {
                title: "View",
                icon: faEye,
                condition: (data: FormEntry) => !data.deleted,
                handler: (data: FormEntry) => {
                    emit(`/histories/view?id=${data.id}`);
                },
            },
            {
                title: "Share and Publish",
                icon: faShareAlt,
                condition: (data: FormEntry) => !data.deleted,
                handler: (data: FormEntry) => {
                    emit(`/histories/sharing?id=${data.id}`);
                },
            },
            {
                title: "Copy",
                icon: faCopy,
                condition: (data: FormEntry) => !data.deleted,
                handler: (data: FormEntry) => {
                    emit(`/histories/sharing?id=${data.id}`);
                },
            },
            {
                title: "Change Permissions",
                icon: faEdit,
                condition: (data: FormEntry) => !data.deleted,
                handler: (data: FormEntry) => {
                    emit(`/histories/permissions?id=${data.id}`);
                },
            },
            {
                title: "Rename",
                icon: faSignature,
                condition: (data: FormEntry) => !data.deleted,
                handler: (data: FormEntry) => {
                    emit(`/histories/rename?id=${data.id}`);
                },
            },
            {
                title: "Delete",
                icon: faTrash,
                condition: (data: FormEntry) => !data.deleted,
                handler: async (data: FormEntry) => {
                    if (confirm(_l("Are you sure that you want to delete this form?"))) {
                        try {
                            await deleteForm({ id: String(data.id) });
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
                condition: (data: FormEntry) => !data.deleted,
                handler: async (data: FormEntry) => {
                    if (confirm(_l("Are you sure that you want to delete this form?"))) {
                        try {
                            await deleteForm({ id: String(data.id) });
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
                title: "Restore",
                icon: faTrashRestore,
                condition: (data: FormEntry) => !!data.deleted,
                handler: async (data: FormEntry) => {
                    try {
                        await undeleteForm({ id: String(data.id) });
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
        key: "hid_counter",
        title: "Items",
        type: "text",
    },
    {
        key: "tags",
        title: "Tags",
        type: "tags",
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
        title: "Sharing",
        type: "sharing",
    },
];

const validFilters: Record<string, ValidFilter<string | boolean | undefined>> = {
    name: { placeholder: "name", type: String, handler: contains("name"), menuItem: true },
    description: { placeholder: "description", type: String, handler: contains("desc"), menuItem: true },
    deleted: {
        placeholder: "Filter on deleted entries",
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
    id: "histories-grid",
    actions: actions,
    fields: fields,
    filtering: new Filtering(validFilters, undefined, false, false),
    getData: getData,
    plural: "Histories",
    sortBy: "name",
    sortDesc: true,
    sortKeys: ["create_time", "name", "update_time"],
    title: "Histories",
};

export default gridConfig;
