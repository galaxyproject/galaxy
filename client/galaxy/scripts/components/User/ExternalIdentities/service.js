/**
 * Data retrieval/storage for the auth keys
 */

import axios from "axios";
import { getRootFromIndexLink } from "onload";

const getUrl = path => getRootFromIndexLink() + path;

export async function disconnectIdentity(doomed) {
    if (doomed) {
        const url = getUrl(`authnz/${doomed.provider}/disconnect/`);
        const response = await axios.delete(url);
        if (response && response.status != 200) {
            throw new Error("Delete failure.");
        }
    }
}

export async function getIdentityProviders() {
    const url = getUrl("authnz");
    const response = await axios.get(url);
    if (response.status != 200) {
        throw new Error("Unable to load connected external identities");
    }
    return response.data;
}

export async function saveIdentity(idp) {
    const url = getUrl(`authnz/${idp}/login`);
    const response = await axios.post(url);
    if (response.status != 200) {
        throw new Error("Save failure.");
    }
    return response;
}

export default {
    saveIdentity,
    disconnectIdentity,
    getIdentityProviders
};
