/**
 * Data retrieval/storage for the auth keys
 */

import axios from "axios";
import { Credential, IdentityProvider } from "./index";
import { getRootFromIndexLink } from "onload";

const getUrl = (path) => getRootFromIndexLink() + path;

export async function listCredentials() {
    const url = getUrl("api/cloud/authz");
    const response = await axios.get(url);
    if (response.status != 200) {
        throw new Error("Unexpected response from listing.");
    }
    return response.data.map(Credential.create);
}

export async function getCredential(id) {
    const url = getUrl("api/cloud/authz/${id}");
    const response = await axios.get(url);
    if (response.status != 200) {
        throw new Error("Unexpected response loading key.");
    }
    return Credential.create(response.data);
}

export async function saveCredential(newItem) {
    const model = Credential.create(newItem);
    const response = await saveOrUpdate(model);
    if (response.status != 200) {
        throw new Error("Save failure.");
    }
    return Credential.create(response.data);
}

async function saveOrUpdate(model) {
    return model.id
        ? axios.put(getUrl(`api/cloud/authz/${model.id}`), model)
        : axios.post(getUrl("api/cloud/authz"), model);
}

export async function deleteCredential(doomed) {
    const model = Credential.create(doomed);
    if (model.id) {
        const url = getUrl(`api/cloud/authz/${doomed.id}`);
        const response = await axios.delete(url);
        if (response.status != 200) {
            throw new Error("Delete failure.");
        }
    }
    return model;
}

// Memoize results (basically never changes)

let identityProviders;

export async function getIdentityProviders() {
    if (!identityProviders) {
        const url = getUrl("authnz");
        const response = await axios.get(url);
        if (response.status != 200) {
            throw new Error("Unable to load identity providers");
        }
        // This should be idempotent (and safe).
        // eslint-disable-next-line require-atomic-updates
        identityProviders = response.data.map(IdentityProvider.create);
    }
    return identityProviders;
}

export default {
    listCredentials,
    getCredential,
    saveCredential,
    deleteCredential,
    getIdentityProviders,
};
