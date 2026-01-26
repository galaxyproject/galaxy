import {
    faClipboard,
    faCloud,
    faCloudDownloadAlt,
    faDatabase,
    faDesktop,
    faFileArchive,
    faHdd,
    faLink,
    faSitemap,
    faTable,
} from "@fortawesome/free-solid-svg-icons";
import { computed, type ComputedRef, defineAsyncComponent } from "vue";

import { useUploadAdvancedMode } from "@/composables/upload/uploadAdvancedMode";

import type { UploadMethod, UploadMethodConfig } from "./types";

export const uploadMethodRegistry: Record<UploadMethod, UploadMethodConfig> = {
    "local-file": {
        id: "local-file",
        name: "Upload from Computer",
        description: "Select and upload files from your local device",
        icon: faDesktop,
        headerAction: "Upload Files",
        requiresTargetHistory: true,
        component: defineAsyncComponent(() => import("./methods/LocalFileUpload.vue")),
    },
    "paste-content": {
        id: "paste-content",
        name: "Paste File Content",
        description: "Paste the content of a file directly",
        icon: faClipboard,
        headerAction: "Paste File Contents and Upload",
        requiresTargetHistory: true,
        component: defineAsyncComponent(() => import("./methods/PasteContentUpload.vue")),
    },
    "paste-links": {
        id: "paste-links",
        name: "Paste Links/URLs",
        description: "Paste URLs to fetch and import data from remote sources",
        icon: faLink,
        headerAction: "Paste Links and Upload",
        requiresTargetHistory: true,
        component: defineAsyncComponent(() => import("./methods/PasteLinksUpload.vue")),
    },
    "remote-files": {
        id: "remote-files",
        name: "Choose Remote Files",
        description: "Select files from configured remote file sources or file repositories",
        icon: faCloud,
        headerAction: "Choose Remote Files",
        requiresTargetHistory: true,
        component: defineAsyncComponent(() => import("./methods/RemoteFilesUpload.vue")),
        requiresConfig: ["file_sources_configured"],
    },
    "data-library": {
        id: "data-library",
        name: "Import from Data Library",
        description: "Select files from Galaxy's data library",
        icon: faDatabase,
        headerAction: "Import from Data Library",
        requiresTargetHistory: true,
        component: defineAsyncComponent(() => import("./methods/DataLibraryUpload.vue")),
    },
    "explore-zip": {
        id: "explore-zip",
        name: "Explore Compressed Zip Archive",
        description: "Browse and select files directly from a compressed zip archive either locally or remotely",
        icon: faFileArchive,
        headerAction: "Extract from Archive",
        requiresTargetHistory: true,
        showStartButton: false,
        component: defineAsyncComponent(() => import("./methods/ExploreZipUpload.vue")),
    },
    "data-source-tools": {
        id: "data-source-tools",
        name: "Data Source Tools",
        description: "Use Galaxy's data source tools to import data from various external sources",
        icon: faCloudDownloadAlt,
        headerAction: "Use Data Source Tools",
        requiresTargetHistory: false,
        showStartButton: false,
        component: defineAsyncComponent(() => import("./methods/DataSourceToolsUpload.vue")),
    },
    "import-history": {
        id: "import-history",
        name: "Import History",
        description: "Import an entire history from a file or URL",
        icon: faHdd,
        headerAction: "Import History",
        requiresTargetHistory: false,
        showStartButton: false,
        component: defineAsyncComponent(() => import("./methods/ImportHistoryUpload.vue")),
    },
    "import-workflow": {
        id: "import-workflow",
        name: "Import Workflow",
        description: "Import a workflow from a file or URL",
        icon: faSitemap,
        headerAction: "Import Workflow",
        requiresTargetHistory: false,
        showStartButton: false,
        component: defineAsyncComponent(() => import("./methods/ImportWorkflowUpload.vue")),
    },
    "rule-based-import": {
        id: "rule-based-import",
        name: "Rule-based Data Import",
        description: "Import datasets or collections using rule-based mappings",
        icon: faTable,
        headerAction: "Launch Rule-based Import",
        requiresTargetHistory: false,
        requiresAdvancedMode: true,
        showStartButton: false,
        component: defineAsyncComponent(() => import("./methods/RuleBasedImportUpload.vue")),
    },
};

export function getUploadMethod(id: UploadMethod): UploadMethodConfig | undefined {
    return uploadMethodRegistry[id];
}

/**
 * Reactive list of all upload methods, automatically filtered based on
 * whether upload advanced mode is enabled.
 */
export function useAllUploadMethods(): ComputedRef<UploadMethodConfig[]> {
    const { advancedMode } = useUploadAdvancedMode();

    return computed(() =>
        Object.values(uploadMethodRegistry).filter((method) => !method.requiresAdvancedMode || advancedMode.value),
    );
}
