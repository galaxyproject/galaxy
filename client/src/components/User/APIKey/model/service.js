import axios from "axios";

import { getAppRoot } from "@/onload/loadConfig";

const getUrl = (path) => getAppRoot() + path;

export async function getAPIKey(userId) {
    const url = getUrl(`api/users/${userId}/api_key/detailed`);
    const response = await axios.get(url);
    if (response.status === 204) {
        return null;
    }
    if (response.status !== 200) {
        throw new Error("Unexpected response retrieving the API key.");
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

export async function deleteAPIKey(userId) {
    const url = getUrl(`api/users/${userId}/api_key`);
    const response = await axios.delete(url);
    if (response.status !== 204) {
        throw new Error("Delete API Key failure.");
    }
}

export default {
    getAPIKey,
    createNewAPIKey,
    deleteAPIKey,
};
