import axios from "axios";
import type Router from "vue-router";

import { fetcher } from "@/api/schema";
import type { ConfigType } from "@/composables/config";
import Filtering, { contains, equals, toBool, type ValidFilter } from "@/utils/filtering";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

const createApiKey = fetcher.path("/api/users/{user_id}/api_key").method("post").create();
const deleteUser = fetcher.path("/api/users/{user_id}").method("delete").create();
const sendActivationEmail = fetcher.path("/api/users/{user_id}/send_activation_email").method("post").create();
const undeleteUser = fetcher.path("/api/users/deleted/{user_id}/undelete").method("post").create();

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
                condition: (data: UserEntry) => !data.deleted && !data.purged,
                handler: (data: UserEntry, router: Router) => {
                    router.push(`/user/information?id=${data.id}`);
                },
            },
            {
                title: "Manage Roles and Groups",
                icon: "users",
                condition: (data: UserEntry) => !data.deleted && !data.purged,
                handler: (data: UserEntry, router: Router) => {
                    router.push(`/admin/form/manage_roles_and_groups_for_user?id=${data.id}`);
                },
            },
            {
                title: "Reset Password",
                icon: "unlock",
                condition: (data: UserEntry) => !data.deleted && !data.purged,
                handler: (data: UserEntry, router: Router) => {
                    router.push(`/admin/form/reset_user_password?id=${data.id}`);
                },
            },
            {
                title: "Recalculate Disk Usage",
                icon: "calculator",
                condition: (data: UserEntry) => !data.deleted && !data.purged,
                handler: async (data: UserEntry) => {
                    try {
                        await sendActivationEmail({ user_id: String(data.id) });
                        return {
                            status: "success",
                            message: `Disk usage of '${data.username}' has been recalculated.`,
                        };
                    } catch (e) {
                        return {
                            status: "danger",
                            message: `Failed to recalculate disk usage of '${data.username}': ${errorMessageAsString(
                                e
                            )}.`,
                        };
                    }
                },
            },
            {
                title: "Send Activation Email",
                icon: "calculator",
                condition: (data: UserEntry, config: ConfigType) => {
                    return config.user_activation_on && !data.deleted && !data.purged;
                },
                handler: async (data: UserEntry) => {
                    try {
                        await sendActivationEmail({ user_id: String(data.id) });
                        return {
                            status: "success",
                            message: `Activation email has been sent to '${data.username}'.`,
                        };
                    } catch (e) {
                        return {
                            status: "danger",
                            message: `Failed to send activation email to '${data.username}': ${errorMessageAsString(
                                e
                            )}.`,
                        };
                    }
                },
            },
            {
                title: "Generate New API Key",
                icon: "key",
                condition: (data: UserEntry) => !data.deleted && !data.purged,
                handler: async (data: UserEntry) => {
                    try {
                        await createApiKey({ user_id: String(data.id) });
                        return {
                            status: "success",
                            message: `New API Key for '${data.username}' has been generated.`,
                        };
                    } catch (e) {
                        return {
                            status: "danger",
                            message: `Failed to generate new API Key for '${data.username}': ${errorMessageAsString(
                                e
                            )}.`,
                        };
                    }
                },
            },
            {
                title: "Delete",
                icon: "trash",
                condition: (data: UserEntry, config: ConfigType) => {
                    return config.allow_user_deletion && !data.deleted && !data.purged;
                },
                handler: async (data: UserEntry) => {
                    try {
                        await deleteUser({ user_id: String(data.id), purge: false });
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
                icon: "trash",
                condition: (data: UserEntry, config: ConfigType) => {
                    return config.allow_user_deletion && data.deleted && !data.purged;
                },
                handler: async (data: UserEntry) => {
                    try {
                        await deleteUser({ user_id: String(data.id), purge: true });
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
                icon: "trash-restore",
                condition: (data: UserEntry, config: ConfigType) => {
                    return config.allow_user_deletion && data.deleted && !data.purged;
                },
                handler: async (data: UserEntry) => {
                    try {
                        await undeleteUser({ user_id: String(data.id) });
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
