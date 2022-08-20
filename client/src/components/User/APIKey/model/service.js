import axios from "axios";
import { getRootFromIndexLink } from "onload";

const getUrl = (path) => getRootFromIndexLink() + path;

export async function listAPIKeys() {
    const url = getUrl(`api/user/api_keys`);
    const response = await axios.get(url);
    if (response.status !== 200) {
        throw new Error("Unexpected response from listing API keys.");
    }
    return response.data;
}

export async function createNewAPIKey() {
    const url = getUrl(`api/user/api_keys`);
    const response = await axios.post(url);
    if (response.status !== 200) {
        throw new Error("Create API key failure.");
    }
    return response.data;
}

export async function deleteAPIKey(id) {
    const url = getUrl(`api/user/api_keys/${id}`);
    const response = await axios.delete(url);
    if (response.status !== 204) {
        throw new Error("Delete API Key failure.");
    }
    return response.data;
}

export default {
    listAPIKeys,
    createNewAPIKey,
    deleteAPIKey,
};
