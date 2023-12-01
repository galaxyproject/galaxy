import {
    faPlus,
    faTrash,
    faTrashRestore,
    faKey,
    faEdit,
} from "@fortawesome/free-solid-svg-icons";
import { useEventBus } from "@vueuse/core";
import axios from "axios";

//import { createApiKey, deleteUser, recalculateDiskUsageByUserId, sendActivationEmail, undeleteUser } from "@/api/users";
import Filtering, { contains, equals, toBool, type ValidFilter } from "@/utils/filtering";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import type { ActionArray, Config, FieldArray } from "./types";

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
                title: "Edit Details",
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
                    try {
                        //await deleteRole({ user_id: String(data.id), purge: false });
                        return {
                            status: "success",
                            message: `'${data.username}' has been deleted.`,
                        };
                    } catch (e) {
                        return {
                            status: "danger",
                            message: `Failed to delete '${data.username}': ${errorMessageAsString(e)}`,
                        };
                    }
                },
            },
            {
                title: "Purge",
                icon: faTrash,
                condition: (data: RoleEntry) => !!data.deleted && !data.purged,
                handler: async (data: RoleEntry) => {
                    try {
                        //await deleteUser({ user_id: String(data.id), purge: true });
                        return {
                            status: "success",
                            message: `'${data.username}' has been purged.`,
                        };
                    } catch (e) {
                        return {
                            status: "danger",
                            message: `Failed to purge '${data.username}': ${errorMessageAsString(e)}`,
                        };
                    }
                },
            },
            {
                title: "Restore",
                icon: faTrashRestore,
                condition: (data: RoleEntry) => !!data.deleted && !data.purged,
                handler: async (data: RoleEntry) => {
                    try {
                        //await undeleteUser({ user_id: String(data.id) });
                        return {
                            status: "success",
                            message: `'${data.username}' has been restored.`,
                        };
                    } catch (e) {
                        return {
                            status: "danger",
                            message: `Failed to restore '${data.username}': ${errorMessageAsString(e)}`,
                        };
                    }
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
        key: "deleted",
        title: "Deleted",
        type: "boolean",
    },
    {
        key: "update_time",
        title: "Updated",
        type: "date",
    },
];

const validFilters: Record<string, ValidFilter<string | boolean | undefined>> = {
    email: { placeholder: "email", type: String, handler: contains("email"), menuItem: true },
    username: { placeholder: "username", type: String, handler: contains("username"), menuItem: true },
    deleted: {
        placeholder: "Filter on deleted entries",
        type: Boolean,
        boolType: "is",
        handler: equals("deleted", "deleted", toBool),
        menuItem: true,
    },
    purged: {
        placeholder: "Filter on purged entries",
        type: Boolean,
        boolType: "is",
        handler: equals("purged", "purged", toBool),
        menuItem: true,
    },
};

/**
 * Grid configuration
 */
const config: Config = {
    id: "roles-grid",
    actions: actions,
    fields: fields,
    filtering: new Filtering(validFilters, undefined, false, false),
    getData: getData,
    plural: "Roles",
    sortBy: "name",
    sortDesc: true,
    sortKeys: ["description", "name", "update_time"],
    title: "Roles",
};

export default config;
