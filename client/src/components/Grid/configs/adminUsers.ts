import axios from "axios";

import Filtering, { contains, equals, toBool, type ValidFilter } from "@/utils/filtering";
import { withPrefix } from "@/utils/redirect";

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
        title: "Email",
        key: "email",
        type: "text",
        width: "30%",
        handler: (data: UserEntry) => {
            window.location.href = withPrefix(`/plugins/visualizations/${data.type}/saved?id=${data.id}`);
        },
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
