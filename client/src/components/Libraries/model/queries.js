import axios from "axios";
import { prependPath } from "utils/redirect";
import { Library } from "./Library";

const api = axios.create({
    baseURL: prependPath("/api"),
});

/**
 * Libraries
 */

export async function getLibraries(params) {
    const response = await api.get(`/libraries?${params.searchQuery}`);
    const rawLibraries = response?.data || [];
    return rawLibraries.map(Library.create);
}

export async function getLibraryById(id) {
    const response = await api.get(`/libraries/${id}`);
    return Library.create(response.data);
}

export async function createLibrary(lib = {}) {
    const response = await api.post("/libraries", lib);
    return Library.create(response.data);
}

export async function saveLibrary(lib = {}) {
    const response = await api.patch(`/libraries/${lib.id}`, lib);
    return Library.create(response.data);
}

export async function deleteLibrary(lib = {}) {
    const response = await api.delete(`/libraries/${lib.id}`, lib);
    return Library.create(response.data);
}

/**
 * Library folder contents
 */

export async function getFolderContents(params) {
    console.log("getFolderContents", params);
}
