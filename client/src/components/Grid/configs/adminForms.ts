import { faEdit, faPlus, faTrash, faTrashRestore } from "@fortawesome/free-solid-svg-icons";
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
type FormEntry = Record<string, unknown>;

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
    const { data } = await axios.get(withPrefix(`/forms/forms_list?${queryString}`));
    return [data.rows, data.rows_total];
}

/**
 * Actions are grid-wide operations
 */
const actions: ActionArray = [
    {
        title: "Create New Form",
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
                title: "Edit",
                icon: faEdit,
                condition: (data: FormEntry) => !data.deleted,
                handler: (data: FormEntry) => {
                    emit(`/admin/form/edit_form?id=${data.id}`);
                },
            },
            {
                title: "Delete",
                icon: faTrash,
                condition: (data: FormEntry) => !data.deleted,
                handler: async (data: FormEntry) => {
                    if (confirm(_l("Are you sure that you want to delete this form?"))) {
                        const { error } = await GalaxyApi().DELETE("/api/forms/{id}", {
                            params: { path: { id: String(data.id) } },
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
                title: "Restore",
                icon: faTrashRestore,
                condition: (data: FormEntry) => !!data.deleted,
                handler: async (data: FormEntry) => {
                    const { error } = await GalaxyApi().POST("/api/forms/{id}/undelete", {
                        params: { path: { id: String(data.id) } },
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
        key: "desc",
        title: "Description",
        type: "text",
    },
    {
        key: "type",
        title: "Type",
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
    description: { placeholder: "description", type: String, handler: contains("desc"), menuItem: true },
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
    id: "forms-grid",
    actions: actions,
    fields: fields,
    filtering: new Filtering(validFilters, undefined, false, false),
    getData: getData,
    plural: "Forms",
    sortBy: "name",
    sortDesc: true,
    sortKeys: ["name", "update_time"],
    title: "Forms",
};

export default gridConfig;
