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
    const { data } = await axios.get(withPrefix("/admin/users_list"));
    const results = [];
    for (const item of data.items) {
        const dataEntry: Record<string, unknown> = {};
        for (const columnKey in item.column_config) {
            const formattedKey = columnKey.toLowerCase().replace(/\s/g, '');
            dataEntry[formattedKey] = item.column_config[columnKey].value;
        }
        results.push(dataEntry);
    }
    const totalMatches = parseInt(data.num_pages);
    return [results, totalMatches];
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
        key: "lastlogin",
        title: "Last Login",
        type: "text",
    },
    {
        key: "diskusage",
        title: "Disk Usage",
        type: "text",
    },
    {
        key: "status",
        title: "Status",
        type: "text",
    },
    {
        key: "created",
        title: "Created",
        type: "text",
    },
    {
        key: "activated",
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
    sortKeys: ["activated", "created", "diskusage", "email", "external", "lastlogin", "status", "username"],
    title: "Users",
};
