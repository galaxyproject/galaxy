import {
    faBolt,
    faCalculator,
    faEnvelope,
    faKey,
    faMask,
    faPlus,
    faTrash,
    faTrashRestore,
    faUnlock,
    faUser,
    faUsers,
} from "@fortawesome/free-solid-svg-icons";
import { useEventBus } from "@vueuse/core";
import axios from "axios";

import { createApiKey, deleteUser, recalculateDiskUsageByUserId, sendActivationEmail, undeleteUser } from "@/api/users";
import { type GalaxyConfiguration } from "@/stores/configurationStore";
import Filtering, { contains, equals, toBool, type ValidFilter } from "@/utils/filtering";
import _l from "@/utils/localization";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import { type ActionArray, type FieldArray, type GridConfig } from "./types";

const { emit } = useEventBus<string>("grid-router-push");

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
    return [data.rows, data.rows_total];
}

/**
 * Actions are grid-wide operations
 */
const actions: ActionArray = [
    {
        title: "Create New User",
        icon: faPlus,
        handler: () => {
            emit("/admin/users/create");
        },
    },
];

/**
 * Declare columns to be displayed
 */
const fields: FieldArray = [
    {
        key: "email",
        title: "Email",
        type: "operations",
        condition: (data: UserEntry) => !data.purged,
        operations: [
            {
                title: "Manage Information",
                icon: faUser,
                condition: (data: UserEntry) => !data.deleted,
                handler: (data: UserEntry) => {
                    emit(`/user/information?id=${data.id}`);
                },
            },
            {
                title: "Manage Roles and Groups",
                icon: faUsers,
                condition: (data: UserEntry) => !data.deleted,
                handler: (data: UserEntry) => {
                    emit(`/admin/form/manage_roles_and_groups_for_user?id=${data.id}`);
                },
            },
            {
                title: "Reset Password",
                icon: faUnlock,
                condition: (data: UserEntry) => !data.deleted,
                handler: (data: UserEntry) => {
                    emit(`/admin/form/reset_user_password?id=${data.id}`);
                },
            },
            {
                title: "Recalculate Disk Usage",
                icon: faCalculator,
                condition: (data: UserEntry) => !data.deleted,
                handler: async (data: UserEntry) => {
                    try {
                        await recalculateDiskUsageByUserId({ user_id: String(data.id) });
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
                title: "Activate",
                icon: faBolt,
                condition: (data: UserEntry, config: GalaxyConfiguration) => {
                    return config.value.user_activation_on && !data.deleted;
                },
                handler: async (data: UserEntry) => {
                    try {
                        await axios.put(withPrefix(`/api/users/${data.id}`), { active: true });
                        return {
                            status: "success",
                            message: `'${data.username}' has been activated.`,
                        };
                    } catch (e) {
                        return {
                            status: "danger",
                            message: `Failed to activate '${data.username}': ${errorMessageAsString(e)}.`,
                        };
                    }
                },
            },
            {
                title: "Send Activation Email",
                icon: faEnvelope,
                condition: (data: UserEntry, config: GalaxyConfiguration) => {
                    return config.value.user_activation_on && !data.deleted;
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
                icon: faKey,
                condition: (data: UserEntry) => !data.deleted,
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
                title: "Impersonate User",
                icon: faMask,
                condition: (data: UserEntry, config: GalaxyConfiguration) => {
                    return config.value.allow_user_impersonation && !data.deleted;
                },
                handler: (data: UserEntry) => {
                    window.location.href = withPrefix(`/admin/impersonate?id=${String(data.id)}`);
                },
            },
            {
                title: "Delete",
                icon: faTrash,
                condition: (data: UserEntry, config: GalaxyConfiguration) => {
                    return config.value.allow_user_deletion && !data.deleted;
                },
                handler: async (data: UserEntry) => {
                    if (confirm(_l("Are you sure that you want to delete this user?"))) {
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
                    }
                },
            },
            {
                title: "Purge",
                icon: faTrash,
                condition: (data: UserEntry, config: GalaxyConfiguration) => {
                    return config.value.allow_user_deletion && data.deleted && !data.purged;
                },
                handler: async (data: UserEntry) => {
                    if (confirm(_l("Are you sure that you want to purge this user?"))) {
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
                    }
                },
            },
            {
                title: "Restore",
                icon: faTrashRestore,
                condition: (data: UserEntry, config: GalaxyConfiguration) => {
                    return config.value.allow_user_deletion && data.deleted && !data.purged;
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
        condition: (data: UserEntry) => !data.purged,
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
        title: "Active",
        type: "boolean",
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
        type: "boolean",
    },
];

const validFilters: Record<string, ValidFilter<string | boolean | undefined>> = {
    email: { placeholder: "email", type: String, handler: contains("email"), menuItem: true },
    username: { placeholder: "username", type: String, handler: contains("username"), menuItem: true },
    deleted: {
        placeholder: "Deleted",
        type: Boolean,
        boolType: "is",
        handler: equals("deleted", "deleted", toBool),
        menuItem: true,
    },
    purged: {
        placeholder: "Purged",
        type: Boolean,
        boolType: "is",
        handler: equals("purged", "purged", toBool),
        menuItem: true,
    },
};

/**
 * Grid configuration
 */
const gridConfig: GridConfig = {
    id: "users-grid",
    actions: actions,
    fields: fields,
    filtering: new Filtering(validFilters, undefined, false, false),
    getData: getData,
    plural: "Users",
    sortBy: "email",
    sortDesc: true,
    sortKeys: ["active", "create_time", "disk_usage", "email", "external", "last_login", "username"],
    title: "Users",
};

export default gridConfig;
