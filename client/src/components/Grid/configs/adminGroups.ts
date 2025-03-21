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
type GroupEntry = Record<string, unknown>;

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
    const { data } = await axios.get(withPrefix(`/admin/groups_list?${queryString}`));
    return [data.rows, data.rows_total];
}

/**
 * Actions are grid-wide operations
 */
const actions: ActionArray = [
    {
        title: "Create New Group",
        icon: faPlus,
        handler: () => {
            emit("/admin/form/create_group");
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
                title: "Edit Name",
                icon: faEdit,
                condition: (data: GroupEntry) => !data.deleted,
                handler: (data: GroupEntry) => {
                    emit(`/admin/form/rename_group?id=${data.id}`);
                },
            },
            {
                title: "Edit Permissions",
                icon: faKey,
                condition: (data: GroupEntry) => !data.deleted,
                handler: (data: GroupEntry) => {
                    emit(`/admin/form/manage_users_and_roles_for_group?id=${data.id}`);
                },
            },
            {
                title: "Delete",
                icon: faTrash,
                condition: (data: GroupEntry) => !data.deleted,
                handler: async (data: GroupEntry) => {
                    if (confirm(_l("Are you sure that you want to delete this group?"))) {
                        const { error } = await GalaxyApi().DELETE("/api/groups/{group_id}", {
                            params: {
                                path: { group_id: String(data.id) },
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
                condition: (data: GroupEntry) => !!data.deleted,
                handler: async (data: GroupEntry) => {
                    if (confirm(_l("Are you sure that you want to purge this group?"))) {
                        const { error } = await GalaxyApi().POST("/api/groups/{group_id}/purge", {
                            params: {
                                path: { group_id: String(data.id) },
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
                condition: (data: GroupEntry) => !!data.deleted,
                handler: async (data: GroupEntry) => {
                    const { error } = await GalaxyApi().POST("/api/groups/{group_id}/undelete", {
                        params: {
                            path: { group_id: String(data.id) },
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
        key: "roles",
        title: "Roles",
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
    id: "groups-grid",
    actions: actions,
    fields: fields,
    filtering: new Filtering(validFilters, undefined, false, false),
    getData: getData,
    plural: "Groups",
    sortBy: "name",
    sortDesc: false,
    sortKeys: ["name", "update_time"],
    title: "Groups",
};

export default gridConfig;
