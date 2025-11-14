import {
    faClipboard,
    faCloud,
    faColumns,
    faDatabase,
    faDesktop,
    faFileArchive,
    faHdd,
    faLink,
    faSitemap,
} from "@fortawesome/free-solid-svg-icons";
import { defineAsyncComponent } from "vue";

import type { UploadMethodConfig, UploadMode } from "./types";

export const uploadMethodRegistry: Record<UploadMode, UploadMethodConfig> = {
    "local-file": {
        id: "local-file",
        name: "Upload from Computer",
        description: "Select and upload files from your local device",
        icon: faDesktop,
        headerAction: "Upload Files",
        isUploadToHistory: true,
        component: defineAsyncComponent(() => import("./methods/LocalFileUpload.vue")),
    },
    "paste-content": {
        id: "paste-content",
        name: "Paste File Content",
        description: "Paste the content of a file directly",
        icon: faClipboard,
        headerAction: "Paste File Contents and Upload",
        isUploadToHistory: true,
        component: defineAsyncComponent(() => import("./methods/PasteContentUpload.vue")),
    },
    "paste-links": {
        id: "paste-links",
        name: "Paste Links/URLs",
        description: "Paste URLs to fetch and import data from remote sources",
        icon: faLink,
        headerAction: "Paste Links and Upload",
        isUploadToHistory: true,
        component: defineAsyncComponent(() => import("./methods/PasteLinksUpload.vue")),
    },
    "collection-upload": {
        id: "collection-upload",
        name: "Upload File Collection",
        description: "Upload multiple files as a collection",
        icon: faColumns,
        headerAction: "Upload Collection",
        isUploadToHistory: true,
        component: defineAsyncComponent(() => import("./methods/CollectionUpload.vue")),
    },
    "remote-files": {
        id: "remote-files",
        name: "Choose Remote Files",
        description: "Select files from configured remote file sources or file repositories",
        icon: faCloud,
        headerAction: "Choose Remote Files",
        isUploadToHistory: true,
        component: defineAsyncComponent(() => import("./methods/RemoteFilesUpload.vue")),
        requiresConfig: ["file_sources_configured"],
    },
    "data-library": {
        id: "data-library",
        name: "Import from Data Library",
        description: "Select files from Galaxy's data library",
        icon: faDatabase,
        headerAction: "Import from Data Library",
        isUploadToHistory: true,
        component: defineAsyncComponent(() => import("./methods/DataLibraryUpload.vue")),
    },
    "explore-zip": {
        id: "explore-zip",
        name: "Explore Compressed Zip Archive",
        description: "Browse and select files directly from a compressed zip archive either locally or remotely",
        icon: faFileArchive,
        headerAction: "Extract from Archive",
        isUploadToHistory: true,
        component: defineAsyncComponent(() => import("./methods/ExploreZipUpload.vue")),
    },
    "import-history": {
        id: "import-history",
        name: "Import History",
        description: "Import an entire history from a file or URL",
        icon: faHdd,
        headerAction: "Import History",
        isUploadToHistory: false,
        component: defineAsyncComponent(() => import("./methods/ImportHistoryUpload.vue")),
    },
    "import-workflow": {
        id: "import-workflow",
        name: "Import Workflow",
        description: "Import a workflow from a file or URL",
        icon: faSitemap,
        headerAction: "Import Workflow",
        isUploadToHistory: false,
        component: defineAsyncComponent(() => import("./methods/ImportWorkflowUpload.vue")),
    },
};

export function getUploadMethod(id: UploadMode): UploadMethodConfig | undefined {
    return uploadMethodRegistry[id];
}

export function getAllUploadMethods(): UploadMethodConfig[] {
    return Object.values(uploadMethodRegistry);
}
