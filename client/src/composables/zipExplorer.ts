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
    const isGalaxyExport = computed(() => zipArchive.value?.entries.find(isGalaxyExportFile) !== undefined);
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

    async function importArtifacts(filesToImport: ZipContentFile[], historyId: string | null) {
        if (!zipArchive.value) {
            throw new Error("No ZIP archive loaded. You must call openZip() first.");
        }

        if (isRemoteZip(zipArchive.value.source)) {
            return handleRemoteZip(zipArchive.value.source, filesToImport, historyId, zipArchive.value);
        }

        return handleLocalZip(filesToImport, historyId, zipArchive.value);
    }

    async function handleRemoteZip(
        zipUrl: string,
        filesToImport: ZipContentFile[],
        historyId: string | null,
        zipArchive: ZipArchive
    ) {
        const toUploadToHistory: ZipFileEntry[] = [];
        for (const file of filesToImport) {
            const entry = zipArchive.entries.filter(isFileEntry).find((e) => e.path === file.path);
            if (!entry) {
                throw new Error(`Selected file not found in ZIP archive: ${file.path}`);
            }

            const extractUrl = toExtractUrl(zipUrl, entry);
            if (isWorkflowFile(file)) {
                try {
                    await axios.post(getFullAppUrl("api/workflows"), { archive_source: extractUrl });
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
                ext: "auto",
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
            await axios.post(getFullAppUrl("api/tools/fetch"), payload);
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async function handleLocalZip(filesToImport: ZipContentFile[], historyId: string | null, zipArchive: ZipArchive) {
        for (const file of filesToImport) {
            const entry = zipArchive.entries.filter(isFileEntry).find((e) => e.path === file.path);
            if (!entry) {
                throw new Error(`Selected file not found in ZIP archive: ${file.path}`);
            }

            if (isWorkflowFile(file)) {
                try {
                    const fileData = await entry.data();
                    const formData = new FormData();
                    formData.append("archive_file", new Blob([fileData]), file.name);

                    await axios.post(getFullAppUrl("api/workflows"), formData);
                } catch (e) {
                    rethrowSimple(e);
                }
            } else {
                await extractFileToDB(entry);
            }
        }

        await uploadExtractedFiles(historyId);
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

    function getEntryName(entry: AnyZipEntry) {
        return entry.path;
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

    function isGalaxyExportFile(entry: AnyZipEntry) {
        return entry.path.endsWith(GALAXY_EXPORT_ATTRS_FILE);
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

    interface IndexedDBFile {
        name: string;
        fileData: Uint8Array;
    }

    const dbName = "zip-extract-db";
    const storeName = "files";
    const extractedFiles = ref<string[]>([]);

    async function openDB(): Promise<IDBDatabase> {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(dbName, 1);
            request.onupgradeneeded = (event: any) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains(storeName)) {
                    db.createObjectStore(storeName, { keyPath: "name" });
                }
            };
            request.onsuccess = () => resolve(request.result);
            request.onerror = (e) => reject(e);
        });
    }

    async function saveToDB(name: string, fileData: Uint8Array) {
        const db = await openDB();
        const tx = db.transaction(storeName, "readwrite");
        const store = tx.objectStore(storeName);
        store.put({ name, fileData });
        db.close();
    }

    async function getFilesFromDB(): Promise<IndexedDBFile[]> {
        const db = await openDB();
        const tx = db.transaction(storeName, "readonly");
        const store = tx.objectStore(storeName);
        const request = store.getAll();
        return new Promise((resolve) => {
            request.onsuccess = () => {
                extractedFiles.value = request.result.map((entry: IndexedDBFile) => entry.name);
                resolve(request.result);
            };
        });
    }

    async function cleanupDatabase() {
        const db = await openDB();
        const tx = db.transaction(storeName, "readwrite");
        const store = tx.objectStore(storeName);
        store.clear();
        extractedFiles.value = [];
        console.log("IndexedDB cleaned up!");
    }

    async function extractFileToDB(entry: ZipFileEntry) {
        const fileData = await entry.data();
        await saveToDB(entry.path.split("/").pop() ?? "unknown", fileData);
    }

    async function uploadExtractedFiles(historyId: string | null) {
        const databaseFiles = await getFilesFromDB();
        if (databaseFiles.length === 0) {
            return; // No files to upload
        }

        if (!historyId) {
            throw new Error("There is no history available to upload the selected files.");
        }

        const files: Blob[] = [];
        const elements = [];

        for (const fileEntry of databaseFiles) {
            const fileBlob = new Blob([fileEntry.fileData]);
            files.push(fileBlob);
            elements.push({
                name: fileEntry.name,
                deferred: false,
                src: "files",
                ext: "auto",
            });
        }

        const target = {
            destination: { type: "hdas" },
            elements: elements,
        };
        const formData = new FormData();
        formData.append("history_id", historyId);
        formData.append("targets", JSON.stringify([target]));
        for (const file of files) {
            formData.append("files", file);
        }

        try {
            await axios.post(getFullAppUrl("api/tools/fetch"), formData);
        } catch (e) {
            rethrowSimple(e);
        }

        await cleanupDatabase(); // Clean up after upload
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

const GALAXY_EXPORT_ATTRS_FILE = "export_attrs.txt";
const GALAXY_HISTORY_EXPORT_ATTRS_FILE = "history_attrs.txt";

export const GALAXY_EXPORT_METADATA_FILES = [
    GALAXY_EXPORT_ATTRS_FILE,
    GALAXY_HISTORY_EXPORT_ATTRS_FILE,
    "collections_attrs.txt",
    "datasets_attrs.txt",
    "datasets_attrs.txt.provenance",
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
