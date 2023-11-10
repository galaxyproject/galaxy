import axios from "axios";
import type Router from "vue-router";

import Filtering, { contains, equals, toBool, type ValidFilter } from "@/utils/filtering";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

/**
 * Local types
 */
type UserEntry = Record<string, unknown>;

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
    const { data } = await axios.get(withPrefix(`/admin/users_list?${queryString}`));
    return [data.rows, data.total_row_count];
}

/**
 * Declare columns to be displayed
 */
const fields = [
    {
        key: "email",
        title: "Email",
        type: "operations",
        condition: (data: UserEntry) => !data.deleted,
        operations: [
            {
                title: "Manage Information",
                icon: "user",
                condition: (data: UserEntry) => !data.deleted,
                handler: (data: UserEntry, router: Router) => {
                    router.push(`/user/information?id=${data.id}`);
                },
            },
            {
                title: "Manage Roles and Groups",
                icon: "users",
                condition: (data: UserEntry) => !data.deleted,
                handler: (data: UserEntry, router: Router) => {
                    router.push(`/admin/form/manage_roles_and_groups_for_user?id=${data.id}`);
                },
            },
            {
                title: "Reset Password",
                icon: "unlock",
                condition: (data: UserEntry) => !data.deleted,
                handler: (data: UserEntry, router: Router) => {
                    router.push(`/admin/form/reset_user_password?id=${data.id}`);
                },
            },
            {
                title: "Recalculate Disk Usage",
                icon: "calculator",
                condition: (data: UserEntry) => !data.deleted,
                handler: async (data: UserEntry) => {
                    try {
                        await axios.put(`/api/visualizations/${data.id}`, { deleted: true });
                        return {
                            status: "success",
                            message: `Disk usage of '${data.title}' has been recalculated.`,
                        };
                    } catch (e) {
                        return {
                            status: "danger",
                            message: `Failed to recalculate disk usage of '${data.title}': ${errorMessageAsString(e)}.`,
                        };
                    }
                },
            },
            {
                title: "Generate New API Key",
                icon: "key",
                condition: (data: UserEntry) => !data.deleted,
                handler: async (data: UserEntry) => {
                    try {
                        await axios.put(`/api/visualizations/${data.id}`, { deleted: true });
                        return {
                            status: "success",
                            message: `New API Key for '${data.title}' has been generated.`,
                        };
                    } catch (e) {
                        return {
                            status: "danger",
                            message: `Failed to generate new API Key for '${data.title}': ${errorMessageAsString(e)}.`,
                        };
                    }
                },
            },
            {
                title: "Delete",
                icon: "trash",
                condition: (data: UserEntry) => !data.deleted /* && config.allow_user_deletion */,
                handler: async (data: UserEntry) => {
                    try {
                        await axios.delete(`/api/users/${data.id}`);
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
                title: "Restore",
                icon: "trash-restore",
                condition: (data: UserEntry) => data.deleted,
                handler: async (data: UserEntry) => {
                    try {
                        await axios.post(`/api/users/deleted/${data.id}/undelete`);
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
        key: "username",
        title: "Username",
        type: "text",
    },
    {
        key: "last_login",
        title: "Last Login",
        type: "text",
    },
    {
        key: "disk_usage",
        title: "Disk Usage",
        type: "text",
    },
    {
        key: "status",
        title: "Status",
        type: "text",
    },
    {
        key: "create_time",
        title: "Created",
        type: "date",
    },
    {
        key: "active",
        title: "Activated",
        type: "text",
    },
    {
        key: "groups",
        title: "Groups",
        type: "text",
    },
    {
        key: "roles",
        title: "Roles",
        type: "text",
    },
    {
        key: "external",
        title: "External",
        type: "text",
    },
];

const validFilters: Record<string, ValidFilter<string | boolean | undefined>> = {
    email: { placeholder: "email", type: String, handler: contains("email"), menuItem: true },
    username: { placeholder: "username", type: String, handler: contains("username"), menuItem: true },
    deleted: {
        placeholder: "Filter on deleted visualizations",
        type: Boolean,
        boolType: "is",
        handler: equals("deleted", "deleted", toBool),
        menuItem: true,
    },
    purged: {
        placeholder: "Filter on purged visualizations",
        type: Boolean,
        boolType: "is",
        handler: equals("purged", "purged", toBool),
        menuItem: true,
    },
};

/**
 * Grid configuration
 */
export default {
    fields: fields,
    filtering: new Filtering(validFilters, undefined, false, false),
    getData: getData,
    plural: "Users",
    sortBy: "email",
    sortDesc: true,
    sortKeys: ["activated", "create_time", "disk_usage", "email", "external", "last_login", "status", "username"],
    title: "Users",
};
