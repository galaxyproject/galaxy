/*
 * Utilities for working with upload data structures.
 */
import { errorMessageAsString, rethrowSimple } from "utils/simple-error";

import { GalaxyApi } from "@/api";
import { getDbKeys } from "@/api/dbKeys";

export const AUTO_EXTENSION = {
    id: "auto",
    text: "Auto-detect",
    description:
        "This system will try to detect the file type automatically. If your file is not detected properly as one of the known formats, it most likely means that it has some format problems (e.g., different number of columns on different rows). You can still coerce the system to set your data to the format you think it should be.  You can also upload compressed files, which will automatically be decompressed.",
};
export const COLLECTION_TYPES = [
    { id: "list", text: "List" },
    { id: "paired", text: "Pair" },
    { id: "list:paired", text: "List of Pairs" },
];
export const DEFAULT_DBKEY = "?";
export const DEFAULT_EXTENSION = "auto";
export const DEFAULT_FILE_NAME = "New File";
export const RULES_TYPES = [
    { id: "collections", text: "Collections" },
    { id: "datasets", text: "Datasets" },
];

/**
 * Local cache.
 */
let _cachedDatatypes;
let _cachedDbKeys;

/*
 * Local helper utilities.
 */
function dbKeySort(defaultDbKey) {
    return (a, b) => {
        if (a.id == defaultDbKey) {
            return -1;
        }
        if (b.id == defaultDbKey) {
            return 1;
        }
        return a.text > b.text ? 1 : a.text < b.text ? -1 : 0;
    };
}

async function loadDbKeys() {
    if (_cachedDbKeys) {
        return _cachedDbKeys;
    }
    const dbKeys = await getDbKeys();
    const dbKeyList = [];
    for (var key in dbKeys) {
        dbKeyList.push({
            id: dbKeys[key][1],
            text: dbKeys[key][0],
        });
    }
    _cachedDbKeys = dbKeyList;
    return dbKeyList;
}

async function loadUploadDatatypes() {
    if (_cachedDatatypes) {
        return _cachedDatatypes;
    }
    const { data: datatypes } = await GalaxyApi().GET("/api/datatypes", {
        params: { query: { extension_only: false } },
    });
    const listExtensions = [];
    for (var key in datatypes) {
        listExtensions.push({
            id: datatypes[key].extension,
            text: datatypes[key].extension,
            description: datatypes[key].description,
            description_url: datatypes[key].description_url,
            composite_files: datatypes[key].composite_files,
            upload_warning: datatypes[key].upload_warning,
        });
    }
    listExtensions.sort((a, b) => {
        var a_text = a.text && a.text.toLowerCase();
        var b_text = b.text && b.text.toLowerCase();
        return a_text > b_text ? 1 : a_text < b_text ? -1 : 0;
    });
    _cachedDatatypes = listExtensions;
    return listExtensions;
}

/*
 * Exported utilities.
 */
export function findExtension(extensions, id) {
    return extensions.find((extension) => extension.id == id) || {};
}

export async function getUploadDatatypes(datatypesDisableAuto, auto) {
    const result = await loadUploadDatatypes();
    const listExtensions = [...result];
    if (!datatypesDisableAuto) {
        listExtensions.unshift(auto);
    }
    return listExtensions;
}

export async function getUploadDbKeys(defaultDbKey) {
    const result = await loadDbKeys();
    const dbKeyList = [...result];
    dbKeyList.sort(dbKeySort(defaultDbKey));
    return dbKeyList;
}

export async function getRemoteEntries(onSuccess, onError) {
    const { data, error } = await GalaxyApi().GET("/api/remote_files");

    if (error) {
        onError(errorMessageAsString(error));
    }

    onSuccess(data);
}

export async function getRemoteEntriesAt(target) {
    const { data: files, error } = await GalaxyApi().GET("/api/remote_files", {
        params: {
            query: { target },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return files;
}

export function hasBrowserSupport() {
    return window.File && window.FormData && window.XMLHttpRequest && window.FileList;
}

export default {
    AUTO_EXTENSION,
    DEFAULT_DBKEY,
    DEFAULT_EXTENSION,
    findExtension,
    getRemoteEntries,
    getRemoteEntriesAt,
    getUploadDatatypes,
    getUploadDbKeys,
};

export function setIframeEvents(elements, disableEvents) {
    let element;
    elements.forEach((e) => {
        element = document.querySelector(`iframe#${e}`);
        if (element) {
            element.style.pointerEvents = disableEvents ? "none" : "auto";
        }
    });
}
