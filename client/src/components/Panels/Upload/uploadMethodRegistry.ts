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
        tips: [
            "Multiple files can be selected at once using Ctrl/Cmd+Click",
            "You can always add more files to the staging area before starting the upload by clicking 'Add More Files' button below",
            "Large files are uploaded in chunks and can automatically resume if your connection drops",
            "If Galaxy cannot detect the file type correctly, you can set it manually before uploading",
            "If you are dealing with text files that use spaces instead of tabs and your downstream tools expect tab-delimited files, consider using the 'Spaces -> Tabs' option available in the upload settings",
        ],
        component: defineAsyncComponent(() => import("./methods/LocalFileUpload.vue")),
    },
    "paste-content": {
        id: "paste-content",
        name: "Paste File Content",
        description: "Paste the content of a file directly",
        icon: faClipboard,
        headerAction: "Paste File Contents and Upload",
        requiresTargetHistory: true,
        tips: [
            "Best suited for small text-based files like tabular data (e.g., TSV, CSV)",
            "Pasting very large content may be slow or fail — use file upload or links for big datasets",
            "You can explicitly set the datatype if Galaxy guesses it incorrectly",
        ],
        component: defineAsyncComponent(() => import("./methods/PasteContentUpload.vue")),
    },
    "paste-links": {
        id: "paste-links",
        name: "Paste Links/URLs",
        description: "Paste URLs to fetch and import data from remote sources",
        icon: faLink,
        headerAction: "Paste Links and Upload",
        requiresTargetHistory: true,
        tips: [
            "Paste one or more URLs (one per line) to stage files for import",
            "Use **deferred** mode to save storage — data will only be downloaded when a tool actually needs it",
            "Deferred datasets behave like normal datasets, but are fetched automatically at runtime. It is recommended to set the correct datatype when using deferred mode, as automatic detection is limited for deferred datasets, since the data is not downloaded immediately",
            "Ideal for very large files hosted on reliable remote servers",
        ],
        component: defineAsyncComponent(() => import("./methods/PasteLinksUpload.vue")),
    },
    "remote-files": {
        id: "remote-files",
        name: "Choose Remote Files",
        description: "Select files from configured remote file sources or file repositories",
        icon: faCloud,
        headerAction: "Choose Remote Files",
        requiresTargetHistory: true,
        tips: [
            "Browse files from connected cloud storage, FTP servers, or institutional data repositories",
            "You can add new remote connections in your user preferences or via the **Connect New Remote Source** button",
            "This is ideal for accessing datasets stored in cloud services without downloading them locally first",
        ],
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
        tips: [
            "Data Libraries contain curated, shared datasets provided by Galaxy administrators",
            "Importing from a library is usually instant and does not duplicate the underlying data",
            "Library datasets are read-only but otherwise behave like normal datasets in your history",
        ],
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
        tips: [
            "Browse the contents of a ZIP archive before importing files",
            "Select only the files you need — you don't have to extract the entire archive",
            "Works with both local ZIP files and remote ZIP URLs. The remote option is useful for large archives hosted on external servers",
        ],
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
        tips: [
            "Use data source tools to import data directly from external databases like NCBI, ENA, or UCSC",
            "These tools often add rich metadata automatically",
            "Recommended when working with public reference datasets",
        ],
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
        tips: [
            "Import a complete Galaxy history from a previously exported file or URL",
            "Useful for sharing analyses or restoring archived work",
            "Imported histories include datasets, metadata, and structure",
        ],
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
        tips: [
            "Import workflows from Galaxy Workflow files or public URLs",
            "This action does not create datasets — it only adds workflows",
            "Learn more about building and sharing workflows at the **Intergalactic Workflow Commission**: [https://iwc.galaxyproject.org/](https://iwc.galaxyproject.org/)",
            "Workflows help automate and standardize analysis pipelines.",
        ],
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
        tips: [
            "Best for importing many files with structured naming conventions",
            "Automatically create dataset collections and assign metadata",
            "Ideal for multi-sample or multi-condition experiments",
        ],
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
