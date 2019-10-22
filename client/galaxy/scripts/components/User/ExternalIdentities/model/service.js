/**
 * Data retrieval/storage for the auth keys
 */

import axios from "axios";
import { Credential, IdentityProvider } from "./index";
import { getRootFromIndexLink } from "onload";

const getUrl = path => getRootFromIndexLink() + path;

/*export async function listIdentities() {
    const url = getUrl("api/cloud/authz");
    const response = await axios.get(url);
    if (response.status != 200) {
        throw new Error("Unexpected response from listing.");
    }
    //return response.data.map(Credential.create);
    return response.data.map(IdentityProvider.create); //testing
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
}*/

export async function disconnectIdentity(doomed) {
    const model = Credential.create(doomed);
    console.log("in disconnect service.js");
    if (doomed) {
        console.log("in  if doomed service.js");
        //const response = await axios.disconnect(getUrl(`authnz/${doomed.id}`));
        const response = await axios.delete(getUrl(`authnz/${doomed.id}`));
        if (response.status != 200) {
            throw new Error("Delete failure.");
        }
        console.log("end of if doomed service.js");
    }
    console.log("end of doomed service.js");
    return model; //testing
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
            throw new Error("Unable to load connected external identities");
        }
        identityProviders = response.data.map(IdentityProvider.create);
    }
    return identityProviders;
}

export default {
    //listIdentities,
    //getCredential,
    //saveCredential,
    disconnectIdentity,
    getIdentityProviders
};
