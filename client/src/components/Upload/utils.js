/*
 * Utilities for working with upload data structures.
 */
import { errorMessageAsString, rethrowSimple } from "utils/simple-error";

import { GalaxyApi } from "@/api";
import { getDbKeys } from "@/api/dbKeys";

export const AUTO_EXTENSION = {
    id: "auto",
    text: "自动检测",
    description:
        "系统将尝试自动检测文件类型。如果您的文件未被正确识别为已知格式之一，很可能意味着它存在格式问题（如不同行的列数不同）。您仍然可以强制系统将数据设置为您认为应有的格式。您也可以上传压缩文件，系统将自动解压。",
};
export const COLLECTION_TYPES = [
    { id: "list", text: "列表" },
    { id: "paired", text: "配对" },
    { id: "list:paired", text: "配对列表" },
];
export const DEFAULT_DBKEY = "?";
export const DEFAULT_EXTENSION = "auto";
export const DEFAULT_FILE_NAME = "新文件";
export const RULES_TYPES = [
    { id: "collections", text: "集合" },
    { id: "datasets", text: "数据集" },
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
