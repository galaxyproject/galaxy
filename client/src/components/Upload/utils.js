/*
 * Utilities for working with upload data structures.
 */
import { fetcher } from "@/schema/fetcher";

const getGenomes = fetcher.path("/api/genomes").method("get").create();

import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";

const AUTO_EXTENSION = {
    id: "auto",
    text: "Auto-detect",
    description:
        "This system will try to detect the file type automatically. If your file is not detected properly as one of the known formats, it most likely means that it has some format problems (e.g., different number of columns on different rows). You can still coerce the system to set your data to the format you think it should be.  You can also upload compressed files, which will automatically be decompressed.",
};
const DEFAULT_DBKEY = "?";
const DEFAULT_EXTENSION = "auto";

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
    const { data } = await getGenomes();
    const dbKeys = data;
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
        return Promise.resolve(_cachedDatatypes);
    }
    const url = `${getAppRoot()}api/datatypes?extension_only=False`;
    return axios
        .get(url)
        .then((response) => {
            const datatypes = response.data;
            const listExtensions = [];
            for (var key in datatypes) {
                listExtensions.push({
                    id: datatypes[key].extension,
                    text: datatypes[key].extension,
                    description: datatypes[key].description,
                    description_url: datatypes[key].description_url,
                    composite_files: datatypes[key].composite_files,
                });
            }
            listExtensions.sort((a, b) => {
                var a_text = a.text && a.text.toLowerCase();
                var b_text = b.text && b.text.toLowerCase();
                return a_text > b_text ? 1 : a_text < b_text ? -1 : 0;
            });
            return listExtensions;
        })
        .then((result) => {
            _cachedDatatypes = result;
            return result;
        });
}

/*
 * Exported utilities.
 */
export function findExtension(extensions, id) {
    return extensions.find((extension) => extension.id == id);
}

export async function getUploadDatatypes(datatypesDisableAuto, auto) {
    return loadUploadDatatypes().then((result) => {
        const listExtensions = [...result];
        if (!datatypesDisableAuto) {
            listExtensions.unshift(auto);
        }
        return listExtensions;
    });
}

export async function getUploadDbKeys(defaultDbKey) {
    return loadDbKeys().then((result) => {
        const dbKeyList = [...result];
        dbKeyList.sort(dbKeySort(defaultDbKey));
        return dbKeyList;
    });
}

export async function getRemoteFiles(success, error) {
    const url = `${getAppRoot()}api/remote_files`;
    try {
        const { data } = await axios.get(url);
        success(data);
    } catch (e) {
        error(rethrowSimple(e));
    }
}

export async function getRemoteFilesAt(target) {
    const url = `${getAppRoot()}api/remote_files?target=${target}`;
    try {
        const response = await axios.get(url);
        const files = response.data;
        return files;
    } catch (e) {
        rethrowSimple(e);
    }
}

export default {
    AUTO_EXTENSION,
    DEFAULT_DBKEY,
    DEFAULT_EXTENSION,
    findExtension,
    getRemoteFiles,
    getRemoteFilesAt,
    getUploadDatatypes,
    getUploadDbKeys,
};
