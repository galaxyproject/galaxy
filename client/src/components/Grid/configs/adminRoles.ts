import { faEdit, faKey, faPlus, faTrash, faTrashRestore } from "@fortawesome/free-solid-svg-icons";
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
type RoleEntry = Record<string, unknown>;

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
    const { data } = await axios.get(withPrefix(`/admin/roles_list?${queryString}`));
    return [data.rows, data.rows_total];
}

/**
 * Actions are grid-wide operations
 */
const actions: ActionArray = [
    {
        title: "Create New Role",
        icon: faPlus,
        handler: () => {
            emit("/admin/form/create_role");
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
                condition: (data: RoleEntry) => !data.deleted,
                handler: (data: RoleEntry) => {
                    emit(`/admin/form/rename_role?id=${data.id}`);
                },
            },
            {
                title: "Edit Permissions",
                icon: faKey,
                condition: (data: RoleEntry) => !data.deleted,
                handler: (data: RoleEntry) => {
                    emit(`/admin/form/manage_users_and_groups_for_role?id=${data.id}`);
                },
            },
            {
                title: "Delete",
                icon: faTrash,
                condition: (data: RoleEntry) => !data.deleted,
                handler: async (data: RoleEntry) => {
                    if (confirm(_l("Are you sure that you want to delete this role?"))) {
                        const { error } = await GalaxyApi().DELETE("/api/roles/{id}", {
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
                condition: (data: RoleEntry) => !!data.deleted,
                handler: async (data: RoleEntry) => {
                    if (confirm(_l("Are you sure that you want to permanently delete this role?"))) {
                        const { error } = await GalaxyApi().POST("/api/roles/{id}/purge", {
                            params: {
                                path: { id: String(data.id) },
                            },
                        });

                        if (error) {
                            return {
                                status: "danger",
                                message: `Failed to permanently delete '${data.name}': ${errorMessageAsString(error)}`,
                            };
                        }

                        return {
                            status: "success",
                            message: `'${data.name}' has been permanently deleted.`,
                        };
                    }
                },
            },
            {
                title: "Restore",
                icon: faTrashRestore,
                condition: (data: RoleEntry) => !!data.deleted,
                handler: async (data: RoleEntry) => {
                    const { error } = await GalaxyApi().POST("/api/roles/{id}/undelete", {
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
        key: "type",
        title: "Type",
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
    id: "roles-grid",
    actions: actions,
    fields: fields,
    filtering: new Filtering(validFilters, undefined, false, false),
    getData: getData,
    plural: "Roles",
    sortBy: "name",
    sortDesc: false,
    sortKeys: ["description", "name", "update_time"],
    title: "Roles",
};

export default gridConfig;
