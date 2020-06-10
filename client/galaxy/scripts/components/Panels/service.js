import axios from "axios";
import { getRootFromIndexLink } from "onload";

const getUrl = (path) => getRootFromIndexLink() + path;

export async function getToolsetList() {
    const url = getUrl("api/toolset");
    const response = await axios.get(url);
    if (response.status != 200) {
        throw new Error("Unable to load list of toolsets.");
    }
    return response.data;
}

export async function getToolsetToolIds(toolset_id) {
    const url = getUrl(`api/toolset/${toolset_id}`);
    //const url = getUrl(`api/toolset/?toolset_id=${toolset_id}`);
    const response = await axios.get(url);

    if (response.status != 200) {
        throw new Error("Unable to load tool ids for toolset.");
    }
    return response.data;
}

export default {
    getToolsetList,
    getToolsetToolIds,
};