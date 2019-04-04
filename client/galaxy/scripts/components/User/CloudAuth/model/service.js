/**
 * Data retrieval/storage for the auth keys
 */

import axios from "axios";
import { Credential, IdentityProvider } from "./index";
import { getRootFromIndexLink } from "onload";

const getUrl = path => getRootFromIndexLink() + path;

export async function listCredentials() {
    let url = getUrl("api/cloud/authz");
    let response = await axios.get(url);
    if (response.status != 200) {
        throw new Error("Unexpected response from listing.");
    }
    return response.data.map(Credential.create);
}

export async function getCredential(id) {
    let url = getUrl("api/cloud/authz/${id}");
    let response = await axios.get(url);
    if (response.status != 200) {
        throw new Error("Unexpected response loading key.");
    }
    return Credential.create(response.data);
}

export async function saveCredential(newItem) {
    let model = Credential.create(newItem);
    let response = await saveOrUpdate(model);
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
    let model = Credential.create(doomed);
    if (model.id) {
        let url = getUrl(`api/cloud/authz/${doomed.id}`);
        let response = await axios.delete(url);
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
        let url = getUrl("authnz");
        let response = await axios.get(url);
        if (response.status != 200) {
            throw new Error("Unable to load identity providers");
        }
        identityProviders = response.data.map(IdentityProvider.create);
    }
    return identityProviders;
}

export default { 
    listCredentials,
    getCredential,
    saveCredential,
    deleteCredential,
    getIdentityProviders
}
