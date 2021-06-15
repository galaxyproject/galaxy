import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import { rethrowSimple } from "utils/simple-error";

const AUTO_EXTENSION = {
    id: "auto",
    text: "Auto-detect",
    description:
        "This system will try to detect the file type automatically. If your file is not detected properly as one of the known formats, it most likely means that it has some format problems (e.g., different number of columns on different rows). You can still coerce the system to set your data to the format you think it should be.  You can also upload compressed files, which will automatically be decompressed.",
};
const DEFAULT_GENOME = "?";
const DEFAULT_EXTENSION = "auto";

export function getUploadDatatypes(datatypesDisableAuto, auto) {
    return loadUploadDatatypes().then((result) => {
        const listExtensions = [...result];
        if (!datatypesDisableAuto) {
            listExtensions.unshift(auto);
        }
        return listExtensions;
    });
}

let _cachedDatatypes;
function loadUploadDatatypes() {
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

export function getUploadGenomes(defaultGenome) {
    return loadGenomes().then((result) => {
        const listGenomes = [...result];
        listGenomes.sort(genomeSort(defaultGenome));
        return listGenomes;
    });
}

const genomeSort = (defaultGenome) => (a, b) => {
    if (a.id == defaultGenome) {
        return -1;
    }
    if (b.id == defaultGenome) {
        return 1;
    }
    return a.text > b.text ? 1 : a.text < b.text ? -1 : 0;
};

let _cachedGenomes;
function loadGenomes() {
    if (_cachedGenomes) {
        return Promise.resolve(_cachedGenomes);
    }
    const url = `${getAppRoot()}api/genomes`;
    return axios
        .get(url)
        .then((response) => {
            const genomes = response.data;
            const listGenomes = [];
            for (var key in genomes) {
                listGenomes.push({
                    id: genomes[key][1],
                    text: genomes[key][0],
                });
            }
            return listGenomes;
        })
        .then((result) => {
            _cachedGenomes = result;
            return result;
        });
}

async function getRemoteFilesAt(target) {
    const url = `${getAppRoot()}api/remote_files?target=${target}`;
    try {
        const response = await axios.get(url);
        const files = response.data;
        return files;
    } catch (e) {
        rethrowSimple(e);
    }
}

function getRemoteFiles(success, error) {
    return $.ajax({
        url: `${getAppRoot()}api/remote_files`,
        method: "GET",
        success: success,
        error: error,
    });
}

export default {
    AUTO_EXTENSION,
    DEFAULT_GENOME,
    DEFAULT_EXTENSION,
    getRemoteFiles,
    getRemoteFilesAt,
    getUploadDatatypes,
    getUploadGenomes,
};
