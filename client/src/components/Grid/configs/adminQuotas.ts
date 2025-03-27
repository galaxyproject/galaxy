import { faCog, faDatabase, faEdit, faPlus, faTrash, faTrashRestore, faUsers } from "@fortawesome/free-solid-svg-icons";
import { useEventBus } from "@vueuse/core";
import axios from "axios";

import { GalaxyApi } from "@/api";
import Filtering, { contains, equals, toBool, type ValidFilter } from "@/utils/filtering";
import _l from "@/utils/localization";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import { type ActionArray, type FieldArray, type GridConfig } from "./types";

const { emit } = useEventBus<string>("grid-router-push");

/**
 * Local types
 */
type QuotaEntry = Record<string, unknown>;

/**
 * Request and return data from server
 */
async function getData(offset: number, limit: number, search: string, sort_by: string, sort_desc: boolean) {
    const query = {
        limit: String(limit),
        offset: String(offset),
        search: search,
        sort_by: sort_by,
        sort_desc: String(sort_desc),
    };
    const queryString = new URLSearchParams(query).toString();
    const { data } = await axios.get(withPrefix(`/admin/quotas_list?${queryString}`));
    return [data.rows, data.rows_total];
}

/**
 * Actions are grid-wide operations
 */
const actions: ActionArray = [
    {
        title: "Create New Quota",
        icon: faPlus,
        handler: () => {
            emit("/admin/form/create_quota");
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
                title: "Edit Name/Description",
                icon: faEdit,
                condition: (data: QuotaEntry) => !data.deleted,
                handler: (data: QuotaEntry) => {
                    emit(`/admin/form/rename_quota?id=${data.id}`);
                },
            },
            {
                title: "Manage Users and Groups",
                icon: faUsers,
                condition: (data: QuotaEntry) => !data.deleted && !data.default_type,
                handler: (data: QuotaEntry) => {
                    emit(`/admin/form/manage_users_and_groups_for_quota?id=${data.id}`);
                },
            },
            {
                title: "Change Amount",
                icon: faDatabase,
                condition: (data: QuotaEntry) => !data.deleted,
                handler: (data: QuotaEntry) => {
                    emit(`/admin/form/edit_quota?id=${data.id}`);
                },
            },
            {
                title: "Change Default",
                icon: faCog,
                condition: (data: QuotaEntry) => !data.deleted,
                handler: (data: QuotaEntry) => {
                    emit(`/admin/form/set_quota_default?id=${data.id}`);
                },
            },
            {
                title: "Delete",
                icon: faTrash,
                condition: (data: QuotaEntry) => !data.deleted,
                handler: async (data: QuotaEntry) => {
                    if (confirm(_l("Are you sure that you want to delete this quota?"))) {
                        const { error } = await GalaxyApi().DELETE("/api/quotas/{id}", {
                            params: {
                                path: { id: String(data.id) },
                            },
                        });

                        if (error) {
                            return {
                                status: "danger",
                                message: `Failed to delete '${data.name}': ${errorMessageAsString(error)}`,
                            };
                        }

                        return {
                            status: "success",
                            message: `'${data.name}' has been deleted.`,
                        };
                    }
                },
            },
            {
                title: "Purge",
                icon: faTrash,
                condition: (data: QuotaEntry) => !!data.deleted,
                handler: async (data: QuotaEntry) => {
                    if (confirm(_l("Are you sure that you want to purge this quota?"))) {
                        const { error } = await GalaxyApi().POST("/api/quotas/{id}/purge", {
                            params: {
                                path: { id: String(data.id) },
                            },
                        });

                        if (error) {
                            return {
                                status: "danger",
                                message: `Failed to purge '${data.name}': ${errorMessageAsString(error)}`,
                            };
                        }

                        return {
                            status: "success",
                            message: `'${data.name}' has been purged.`,
                        };
                    }
                },
            },
            {
                title: "Restore",
                icon: faTrashRestore,
                condition: (data: QuotaEntry) => !!data.deleted,
                handler: async (data: QuotaEntry) => {
                    const { error } = await GalaxyApi().POST("/api/quotas/deleted/{id}/undelete", {
                        params: {
                            path: { id: String(data.id) },
                        },
                    });

                    if (error) {
                        return {
                            status: "danger",
                            message: `Failed to restore '${data.name}': ${errorMessageAsString(error)}`,
                        };
                    }

                    return {
                        status: "success",
                        message: `'${data.name}' has been restored.`,
                    };
                },
            },
        ],
    },
    {
        key: "description",
        title: "Description",
        type: "text",
    },
    {
        key: "amount",
        title: "Amount",
        type: "text",
    },
    {
        key: "groups",
        title: "Groups",
        type: "text",
    },
    {
        key: "users",
        title: "Users",
        type: "text",
    },
    {
        key: "default_type",
        title: "Default",
        type: "text",
    },
    {
        key: "quota_source_label",
        title: "Source",
        type: "text",
    },
    {
        key: "update_time",
        title: "Updated",
        type: "date",
    },
];

const validFilters: Record<string, ValidFilter<string | boolean | undefined>> = {
    name: { placeholder: "name", type: String, handler: contains("name"), menuItem: true },
    description: { placeholder: "description", type: String, handler: contains("description"), menuItem: true },
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
    id: "quotas-grid",
    actions: actions,
    fields: fields,
    filtering: new Filtering(validFilters, undefined, false, false),
    getData: getData,
    plural: "Quotas",
    sortBy: "name",
    sortDesc: false,
    sortKeys: ["name", "description", "update_time"],
    title: "Quotas",
};

export default gridConfig;
