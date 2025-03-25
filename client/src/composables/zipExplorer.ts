import axios from "axios";
import {
    type AnyZipEntry,
    isFileEntry,
    isRemoteZip,
    ROCrateZipExplorer,
    type ZipArchive,
    type ZipFileEntry,
} from "ro-crate-zip-explorer";
import { computed, ref } from "vue";

import { getFullAppUrl } from "@/app/utils";
import { errorMessageAsString, rethrowSimple } from "@/utils/simple-error";

const zipExplorer = ref<ROCrateZipExplorer>();
const zipArchive = ref<ZipArchive>();
const zipExplorerError = ref<string>();

export function useZipExplorer() {
    const isLoading = ref(false);

    const isRoCrate = computed(() => zipExplorer.value?.hasCrate);
    const isGalaxyExport = computed(() => zipArchive.value?.findFileByName("export_attrs.txt") !== undefined);
    const isZipArchiveAvailable = computed(() => zipArchive.value !== undefined);

    async function openZip(zipSource: File | string) {
        if (typeof zipSource === "string") {
            if (!isValidUrl(zipSource)) {
                zipExplorerError.value = "Invalid URL provided for zip archive";
                return;
            }
            zipSource = getProxiedUrl(zipSource);
        }
        zipExplorerError.value = undefined;
        isLoading.value = true;
        try {
            const explorer = new ROCrateZipExplorer(zipSource);
            zipExplorer.value = explorer;
            zipArchive.value = await explorer.open();
        } catch (e) {
            zipExplorerError.value = errorMessageAsString(e);
        } finally {
            isLoading.value = false;
        }
    }

    async function importArtifacts(filesToImport: ZipContentFile[], historyId: string | null) {
        if (!zipArchive.value) {
            throw new Error("No ZIP archive loaded. You must call openZip() first.");
        }

        const selectedPaths = filesToImport.map((item) => item.path);
        const selectedZipEntries = zipArchive.value.entries.filter((entry) => selectedPaths.includes(entry.path));

        if (isRemoteZip(zipArchive.value.source)) {
            const zipUrl = zipArchive.value.source;
            const toUploadToHistory: ZipFileEntry[] = [];
            for (const file of filesToImport) {
                const entry = zipArchive.value.entries.filter(isFileEntry).find((e) => e.path === file.path);
                if (!entry) {
                    throw new Error(`Selected file not found in ZIP archive: ${file.path}`);
                }

                const extractUrl = toExtractUrl(zipUrl, entry);
                if (isWorkflowFile(file)) {
                    try {
                        await axios.post(getFullAppUrl("/api/workflows"), { archive_source: extractUrl });
                    } catch (e) {
                        rethrowSimple(e);
                    }
                } else {
                    toUploadToHistory.push(entry);
                }
            }

            if (toUploadToHistory.length === 0) {
                return;
            }

            if (!historyId) {
                throw new Error("There is no history available to upload the selected files.");
            }

            const elements = toUploadToHistory.map((entry) => {
                const extractUrl = toExtractUrl(zipUrl, entry);
                return {
                    name: entry.path.split("/").pop() ?? "unknown",
                    deferred: false,
                    src: "url",
                    url: extractUrl,
                    // dbkey: item.dbKey ?? "?",
                    // ext: item.extension ?? "auto",
                    // space_to_tab: item.spaceToTab,
                    // to_posix_lines: item.toPosixLines,
                };
            });
            const target = {
                destination: { type: "hdas" },
                elements: elements,
            };
            const payload = {
                history_id: historyId,
                targets: [target],
            };
            try {
                await axios.post(getFullAppUrl("/api/tools/fetch"), payload);
            } catch (e) {
                rethrowSimple(e);
            }
        }
        //TODO: handle local zip files. This will require downloading the compressed file to a temporary location and then extracting and uploading the selected files.

        console.log("Selected entries:", selectedZipEntries);
    }

    function toExtractUrl(zipUrl: string, entry: ZipFileEntry): string {
        return `zip://extract?source=${zipUrl}&header_offset=${entry.headerOffset}&compress_size=${entry.compressSize}&compression_method=${entry.compressionMethod}`;
    }

    function isWorkflowFile(item: ZipContentFile): boolean {
        return item.type === "workflow";
    }

    function reset() {
        zipExplorer.value = undefined;
        zipArchive.value = undefined;
        zipExplorerError.value = undefined;
    }

    function getImportableZipContents(): ImportableZipContents | undefined {
        if (!zipArchive.value) {
            return undefined;
        }

        const workflows: ZipContentFile[] = [];
        const files: ZipContentFile[] = [];
        for (const entry of zipArchive.value.entries) {
            if (shouldSkipZipEntry(entry)) {
                continue;
            }

            const baseFile = {
                name: getEntryName(entry),
                path: entry.path,
            };

            if (isGalaxyWorkflow(entry)) {
                workflows.push({
                    ...baseFile,
                    type: "workflow",
                });
            } else {
                files.push({
                    ...baseFile,
                    type: "file",
                });
            }
        }
        return { workflows, files };
    }

    function getEntryName(entry: AnyZipEntry) {
        return entry.path.split("/").pop() || entry.path;
    }

    function shouldSkipZipEntry(entry: AnyZipEntry) {
        return (
            entry.type == "Directory" ||
            GALAXY_EXPORT_METADATA_FILES.some((ignoredFile) => entry.path.includes(ignoredFile))
        );
    }

    function isGalaxyWorkflow(entry: AnyZipEntry) {
        return entry.path.endsWith(".gxwf.yml");
    }

    function isValidUrl(inputUrl?: string) {
        if (!inputUrl) {
            return false;
        }
        let url;
        try {
            url = new URL(inputUrl);
        } catch {
            return false;
        }

        return url.protocol === "http:" || url.protocol === "https:";
    }

    /**
     * To avoid CORS issues, we proxy the URL through the Galaxy server.
     */
    function getProxiedUrl(url: string) {
        const proxyUrl = getFullAppUrl(`/api/proxy?url=${encodeURIComponent(url)}`);
        return proxyUrl;
    }

    return {
        zipExplorer,
        zipArchive,
        errorMessage: zipExplorerError,
        isLoading,
        isRoCrate,
        isGalaxyExport,
        isZipArchiveAvailable,
        openZip,
        reset,
        isValidUrl,
        getImportableZipContents,
        importArtifacts,
    };
}

export function isZipFile(file?: File | null): string {
    if (!file) {
        return "No file selected";
    }

    if (file.type !== "application/zip") {
        return "Invalid file type. Please select a ZIP file.";
    }

    return "";
}

export const GALAXY_EXPORT_METADATA_FILES = [
    "collections_attrs.txt",
    "datasets_attrs.txt",
    "datasets_attrs.txt.provenance",
    "export_attrs.txt",
    "implicit_collection_jobs_attrs.txt",
    "implicit_dataset_conversions.txt",
    "invocation_attrs.txt",
    "jobs_attrs.txt",
    "libraries_attrs.txt",
    "library_folders_attrs.txt",
];

export interface ZipContentFile {
    name: string;
    path: string;
    type: "workflow" | "file";
}

export interface ImportableZipContents {
    workflows: ZipContentFile[];
    files: ZipContentFile[];
}
