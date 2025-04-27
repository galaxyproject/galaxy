import axios from "axios";
import {
    AbstractZipExplorer,
    type AnyZipEntry,
    isFileEntry,
    isRemoteZip,
    type IZipExplorer,
    ROCrateZipExplorer,
    type ZipEntryMetadata,
    ZipExplorer,
    type ZipFileEntry,
} from "ro-crate-zip-explorer";
import { computed, ref } from "vue";

import { getFullAppUrl } from "@/app/utils";
import { useIndexedDBFileStorage } from "@/composables/localFileStore";
import { errorMessageAsString, rethrowSimple } from "@/utils/simple-error";

export { isFileEntry, type IZipExplorer, ROCrateZipExplorer } from "ro-crate-zip-explorer";

const zipExplorer = ref<IZipExplorer>();
const zipExplorerError = ref<string>();

export function useZipExplorer() {
    const isLoading = ref(false);

    const isZipArchiveAvailable = computed(() => zipExplorer.value?.zipArchive !== undefined);

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
            const basicExplorer = new ZipExplorer(zipSource);
            await basicExplorer.open();
            const explorer = selectZipExplorerByContent(basicExplorer);
            await explorer.extractMetadata();
            zipExplorer.value = explorer;
        } catch (e) {
            zipExplorerError.value = errorMessageAsString(e);
        } finally {
            isLoading.value = false;
        }
    }

    async function importArtifacts(filesToImport: ImportableFile[], historyId: string | null) {
        if (!zipExplorer.value) {
            throw new Error("No archive loaded. You must call openZip() first.");
        }
        const zipSource = zipExplorer.value.zipArchive.source;

        if (isRemoteZip(zipSource)) {
            const originalUrl = getOriginalUrl(zipSource);
            return handleRemoteZip(originalUrl, filesToImport, historyId, zipExplorer.value);
        }

        return handleLocalZip(filesToImport, historyId, zipExplorer.value);
    }

    async function handleRemoteZip(
        zipUrl: string,
        filesToImport: ImportableFile[],
        historyId: string | null,
        zipExplorer: IZipExplorer
    ) {
        const toUploadToHistory: { file: ImportableFile; entry: ZipFileEntry }[] = [];
        for (const file of filesToImport) {
            const entry = zipExplorer.entries.get(file.path);
            if (!entry) {
                throw new Error(`Selected file not found in archive: ${file.path}`);
            }
            if (!isFileEntry(entry)) {
                throw new Error(`Selected file is not a valid file entry: ${file.path}`);
            }

            const extractUrl = toExtractUrl(zipUrl, entry);
            if (isWorkflowFile(file)) {
                try {
                    await axios.post(getFullAppUrl("api/workflows"), { archive_source: extractUrl });
                } catch (e) {
                    rethrowSimple(e);
                }
            } else {
                toUploadToHistory.push({ file, entry });
            }
        }

        if (toUploadToHistory.length === 0) {
            return;
        }

        if (!historyId) {
            throw new Error("There is no history available to upload the selected files.");
        }

        const elements = toUploadToHistory.map(({ file, entry }) => {
            const extractUrl = toExtractUrl(zipUrl, entry);
            const name = file.name ?? entry.path.split("/").pop() ?? "unknown";

            return {
                name,
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

    async function handleLocalZip(
        filesToImport: ImportableFile[],
        historyId: string | null,
        zipExplorer: IZipExplorer
    ) {
        for (const file of filesToImport) {
            const entry = zipExplorer.entries.get(file.path);

            if (!entry) {
                throw new Error(`Selected file not found in archive: ${file.path}`);
            }

            if (!isFileEntry(entry)) {
                throw new Error(`Selected file is not a valid file entry: ${file.path}`);
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

        await uploadExtractedFiles(historyId, filesToImport);
    }

    function toExtractUrl(zipUrl: string, entry: ZipFileEntry): string {
        return `zip://extract?source=${zipUrl}&header_offset=${entry.headerOffset}&compress_size=${entry.compressSize}&compression_method=${entry.compressionMethod}`;
    }

    function isWorkflowFile(item: ImportableFile): boolean {
        return item.type === "workflow";
    }

    function reset() {
        zipExplorer.value = undefined;
        zipExplorerError.value = undefined;
        clearDatabaseStore();
    }

    function isValidUrl(inputUrl?: string | null) {
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
        const proxyUrl = getFullAppUrl(`api/proxy?url=${encodeURIComponent(url)}`);
        return proxyUrl;
    }

    function getOriginalUrl(maybeProxyUrl: string) {
        if (!maybeProxyUrl.startsWith(getFullAppUrl("api/proxy"))) {
            return maybeProxyUrl;
        }
        // Extract the original URL from the proxied URL
        const url = new URL(maybeProxyUrl);
        const originalUrl = decodeURIComponent(url.searchParams.get("url") ?? "");
        return originalUrl;
    }

    const { storeFile, getAllStoredFiles, clearDatabaseStore } = useIndexedDBFileStorage({
        name: "zip-extract-db",
        store: "files",
        version: 1,
    });

    async function extractFileToDB(entry: ZipFileEntry) {
        const fileData = await entry.data();
        const fileBlob = new Blob([fileData]);
        await storeFile(entry.path, fileBlob);
    }

    async function uploadExtractedFiles(historyId: string | null, filesToImport: ImportableFile[]) {
        const databaseFiles = await getAllStoredFiles();
        if (databaseFiles.length === 0) {
            return; // No files to upload
        }

        if (!historyId) {
            throw new Error("There is no history available to upload the selected files.");
        }

        const files: Blob[] = [];
        const elements = [];

        for (const fileEntry of databaseFiles) {
            const file = filesToImport.find((file) => file.path === fileEntry.name);
            if (!file) {
                continue; // File not selected for import
            }
            files.push(fileEntry.fileData);
            elements.push({
                name: file.name,
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

        await clearDatabaseStore();
    }

    function isZipOpen(zipSource: File | string): boolean {
        if (!zipExplorer.value) {
            return false;
        }
        const currentSource = zipExplorer.value.zipArchive.source;
        if (isRemoteZip(currentSource) && isRemoteZip(zipSource)) {
            return currentSource === getProxiedUrl(zipSource);
        }
        return zipSource === currentSource;
    }

    return {
        zipExplorer,
        errorMessage: zipExplorerError,
        isLoading,
        isZipArchiveAvailable,
        openZip,
        reset,
        isValidUrl,
        importArtifacts,
        isZipOpen,
    };
}

export function getImportableFiles(explorer: IZipExplorer): ImportableFile[] {
    const files: ImportableFile[] = [];
    for (const entry of explorer.entries.values()) {
        if (!isFileEntry(entry)) {
            continue;
        }

        if (shouldSkipZipEntry(entry)) {
            continue;
        }

        const baseFile = explorer.getFileEntryMetadata(entry);
        files.push({
            ...baseFile,
            type: isGalaxyWorkflow(entry) ? "workflow" : "file",
        });
    }
    files.sort(orderByPath);
    return files;
}

/**
 * Order files by their path putting root files first.
 */
function orderByPath(a: ZipEntryMetadata, b: ZipEntryMetadata) {
    const aPath = a.path.split("/");
    const bPath = b.path.split("/");
    if (aPath.length === 1 && bPath.length > 1) {
        return -1;
    }
    if (aPath.length > 1 && bPath.length === 1) {
        return 1;
    }
    return a.path.localeCompare(b.path);
}

/**
 * Check if the entry should be skipped based on its path.
 * This includes common known files to skip, hidden files (starting with a dot),
 * and files from the __MACOSX directory.
 */
function shouldSkipZipEntry(entry: ZipFileEntry) {
    const fileName = entry.path.split("/").pop() ?? "";
    return COMMON_KNOWN_FILES_TO_SKIP.has(fileName) || fileName.startsWith(".") || entry.path.startsWith("__MACOSX");
}

function isGalaxyWorkflow(entry: AnyZipEntry) {
    return entry.path.endsWith(".gxwf.yml");
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

export function isRoCrateZip(explorer?: IZipExplorer): explorer is ROCrateZipExplorer {
    return explorer !== undefined && hasRoCrateMetadata(explorer);
}

export function isGalaxyZipExport(explorer?: IZipExplorer): explorer is GalaxyZipExplorer {
    return explorer !== undefined && hasGalaxyExportMetadata(explorer);
}

export function isGalaxyHistoryExport(explorer?: IZipExplorer): explorer is GalaxyZipExplorer {
    return explorer !== undefined && hasGalaxyHistoryExportMetadata(explorer);
}

const GALAXY_EXPORT_ATTRS_FILE = "export_attrs.txt";
const GALAXY_HISTORY_EXPORT_ATTRS_FILE = "history_attrs.txt";
const GALAXY_DATASET_ATTRS_FILE = "datasets_attrs.txt";

const GALAXY_EXPORT_METADATA_FILES = new Set([
    GALAXY_EXPORT_ATTRS_FILE,
    GALAXY_HISTORY_EXPORT_ATTRS_FILE,
    GALAXY_DATASET_ATTRS_FILE,
    "collections_attrs.txt",
    "datasets_attrs.txt.provenance",
    "implicit_collection_jobs_attrs.txt",
    "implicit_dataset_conversions.txt",
    "invocation_attrs.txt",
    "jobs_attrs.txt",
    "libraries_attrs.txt",
    "library_folders_attrs.txt",
]);

const ROCRATE_METADATA_FILE = "ro-crate-metadata.json";
const ROCRATE_METADATA_FILES = new Set([ROCRATE_METADATA_FILE, "ro-crate-preview.html"]);

const COMMON_KNOWN_FILES_TO_SKIP = new Set([...GALAXY_EXPORT_METADATA_FILES, ...ROCRATE_METADATA_FILES]);

export interface ImportableFile extends ZipEntryMetadata {
    type: "workflow" | "file";
}

export interface ImportableZipContents {
    workflows: ImportableFile[];
    files: ImportableFile[];
}

interface DatasetAttrs {
    file_name: string;
    name?: string;
    annotation?: string;
    peek?: string;
    extension?: string;
    blurb?: string;
}

export class GalaxyZipExplorer extends AbstractZipExplorer {
    private datasetAttrs?: Map<string, Partial<ZipEntryMetadata>>;

    protected async loadMetadata(): Promise<void> {
        if (!this.datasetAttrs) {
            const datasetAttrsFile = this.explorer.zipArchive.findFileByName(GALAXY_DATASET_ATTRS_FILE);
            if (datasetAttrsFile) {
                const json = await this.fetchFileAsJSON(datasetAttrsFile);
                this.datasetAttrs = new Map<string, Partial<ZipEntryMetadata>>();
                for (const value of Object.values(json)) {
                    if (this.hasDatasetAttrs(value)) {
                        this.datasetAttrs.set(value["file_name"], {
                            name: value.name,
                            description: value.annotation,
                        });
                    }
                }
            }
        }
    }

    protected extractPartialZipEntryMetadata(entry: ZipFileEntry): Partial<ZipEntryMetadata> {
        const metadata = this.datasetAttrs?.get(entry.path);
        return {
            name: metadata?.["name"] as string,
            description: metadata?.["description"] as string,
        };
    }

    private async fetchFileAsJSON(file: ZipFileEntry): Promise<Record<string, unknown>> {
        const fileData = await file.data();
        const fileJson = new TextDecoder().decode(fileData);
        return JSON.parse(fileJson) as Record<string, unknown>;
    }

    private hasDatasetAttrs(value: unknown): value is DatasetAttrs {
        return (
            typeof value === "object" &&
            value !== null &&
            "file_name" in value &&
            typeof (value as DatasetAttrs)["file_name"] === "string"
        );
    }
}

function hasRoCrateMetadata(zipExplorer: IZipExplorer): boolean {
    return zipExplorer.zipArchive.findFileByName(ROCRATE_METADATA_FILE) !== undefined;
}

function hasGalaxyExportMetadata(zipExplorer: IZipExplorer): boolean {
    return zipExplorer.zipArchive.findFileByName(GALAXY_EXPORT_ATTRS_FILE) !== undefined;
}

function hasGalaxyHistoryExportMetadata(zipExplorer: IZipExplorer): boolean {
    return zipExplorer.zipArchive.findFileByName(GALAXY_HISTORY_EXPORT_ATTRS_FILE) !== undefined;
}

function selectZipExplorerByContent(zipExplorer: IZipExplorer): IZipExplorer {
    if (hasRoCrateMetadata(zipExplorer)) {
        return new ROCrateZipExplorer(zipExplorer);
    }

    if (hasGalaxyExportMetadata(zipExplorer)) {
        return new GalaxyZipExplorer(zipExplorer);
    }
    return zipExplorer;
}
