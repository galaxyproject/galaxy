import axios from "axios";
import { getRootFromIndexLink } from "onload";

const getUrl = (path) => getRootFromIndexLink() + path;

export async function disconnectIdentity(doomed) {
    if (doomed) {
        let url;
        if (doomed.provider === "custos" || doomed.provider === "cilogon") {
            url = getUrl(`authnz/${doomed.provider}/disconnect/${doomed.email}`);
        } else {
            url = getUrl(`authnz/${doomed.provider}/disconnect/`);
        }

        const response = await axios.delete(url);
        if (response.status != 200) {
            throw new Error("删除失败。");
        }
    }
}

// 缓存结果（基本不会改变）
let identityProviders;

export async function getIdentityProviders() {
    const url = getUrl("authnz");
    const response = await axios.get(url);
    if (response.status != 200) {
        throw new Error("无法加载关联的外部身份");
    }
    identityProviders = response.data;
    return identityProviders;
}

export async function saveIdentity(idp) {
    const url = getUrl(`authnz/${idp}/login`);
    const response = await axios.post(url);
    if (response.status != 200) {
        throw new Error("Save failure.");
    }
    return response;
}

export async function hasUsername() {
    const result = getCurrentUser();
    console.log(result.username);
    return getCurrentUser().username;
}

export async function getCurrentUser() {
    const url = getUrl("api/users/current");
    const response = await axios.get(url);
    if (response.status != 200) {
        throw new Error(response);
    }
    return response.data;
}

export default {
    saveIdentity,
    disconnectIdentity,
    getIdentityProviders,
    hasUsername,
};
