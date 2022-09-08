import axios from "axios";
import { getRootFromIndexLink } from "onload";

const getUrl = (path) => getRootFromIndexLink() + path;

export async function listAPIKeys(userId) {
    const url = getUrl(`api/users/${userId}/api_key`);
    const response = await axios.get(url);
    if (response.status === 204) {
        return [];
    }
    if (response.status !== 200) {
        throw new Error("Unexpected response from listing API keys.");
    }
    return [response.data];
}

export async function createNewAPIKey(userId) {
    const url = getUrl(`api/users/${userId}/api_key`);
    const response = await axios.post(url);
    if (response.status !== 200) {
        throw new Error("Create API key failure.");
    }
    return response.data;
}

export async function deleteAPIKey(userId, key) {
    const url = getUrl(`api/users/${userId}/api_key/${key}`);
    const response = await axios.delete(url);
    if (response.status !== 204) {
        throw new Error("Delete API Key failure.");
    }
}

export default {
    listAPIKeys,
    createNewAPIKey,
    deleteAPIKey,
};
