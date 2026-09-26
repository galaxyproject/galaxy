import type { DataUri } from "../types";

export const SINGULAR_DATA_URI: DataUri = {
    src: "url",
    location: "link_to_file",
    ext: "txt",
};

export const SINGULAR_FILE_URI: DataUri = {
    class: "File",
    ext: "txt",
    location: "link_to_file",
};

export const SINGULAR_LIST_URI: DataUri = {
    class: "Collection",
    collection_type: "list",
    elements: [
        {
            class: "File",
            ext: "txt",
            location: "link_to_file",
            identifier: "1.bed",
        },
        {
            class: "File",
            ext: "txt",
            location: "link_to_file",
            identifier: "2.bed",
        },
        {
            class: "File",
            ext: "txt",
            location: "link_to_file",
            identifier: "3.bed",
        },
    ],
};
