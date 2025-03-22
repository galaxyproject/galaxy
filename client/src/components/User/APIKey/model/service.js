import axios from "axios";
import { getRootFromIndexLink } from "onload";

const getUrl = (path) => getRootFromIndexLink() + path;

export async function getAPIKey(userId) {
    const url = getUrl(`api/users/${userId}/api_key/detailed`);
    const response = await axios.get(url);
    if (response.status === 204) {
        return [];
    }
    if (response.status !== 200) {
        throw new Error("获取API密钥时出现意外响应。");
    }
    return [response.data];
}

export async function createNewAPIKey(userId) {
    const url = getUrl(`api/users/${userId}/api_key`);
    const response = await axios.post(url);
    if (response.status !== 200) {
        throw new Error("创建API密钥失败。");
    }
    return response.data;
}

export async function deleteAPIKey(userId) {
    const url = getUrl(`api/users/${userId}/api_key`);
    const response = await axios.delete(url);
    if (response.status !== 204) {
        throw new Error("删除API密钥失败。");
    }
}

export default {
    getAPIKey,
    createNewAPIKey,
    deleteAPIKey,
};
