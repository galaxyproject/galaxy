import Filtering from "@/utils/filtering";
import { withPrefix } from "@/utils/redirect";
import axios from "axios";

/**
 * Local types
 */
type UserEntry = Record<string, unknown>;

/**
 * Request and return data from server
 */
async function getData(offset: number, limit: number, search: string, sort_by: string, sort_desc: boolean) {
    const { data } = await axios.get(withPrefix(`/admin/users_list?sort_by=${sort_by}&sort_desc=${sort_desc}`));
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

/**
 * Grid configuration
 */
export default {
    fields: fields,
    filtering: new Filtering({}, undefined, false, false),
    getData: getData,
    plural: "Users",
    sortBy: "email",
    sortDesc: true,
    sortKeys: ["activated", "create_time", "disk_usage", "email", "external", "last_login", "status", "username"],
    title: "Users",
};
