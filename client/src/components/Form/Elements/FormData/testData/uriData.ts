import type { DataUri } from "../types";

export const SINGULAR_DATA_URI: DataUri = {
    src: "url",
    url: "link_to_file",
    ext: "txt",
};

export const SINGULAR_FILE_URI: DataUri = {
    class: "File",
    filetype: "txt",
    location: "link_to_file",
};

export const SINGULAR_FILE_URI_ALIAS: DataUri = {
    class: "File",
    extension: "txt",
    url: "link_to_file",
};

export const SINGULAR_LIST_URI: DataUri = {
    class: "Collection",
    collection_type: "list",
    elements: [
        {
            class: "File",
            filetype: "txt",
            location: "link_to_file",
            identifier: "1.bed",
        },
        {
            class: "File",
            filetype: "txt",
            location: "link_to_file",
            identifier: "2.bed",
        },
        {
            class: "File",
            filetype: "txt",
            location: "link_to_file",
            identifier: "3.bed",
        },
    ],
};

export const SINGULAR_LIST_URI_ALIAS: DataUri = {
    class: "Collection",
    collection_type: "list",
    elements: [
        {
            class: "File",
            url: "link_to_file",
            ext: "txt",
            identifier: "1.bed",
        },
        {
            class: "File",
            url: "link_to_file",
            ext: "txt",
            identifier: "2.bed",
        },
        {
            class: "File",
            url: "link_to_file",
            ext: "txt",
            identifier: "3.bed",
        },
    ],
};
