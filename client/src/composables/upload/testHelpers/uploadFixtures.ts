import type { UploadCollectionConfig } from "@/composables/upload/collectionTypes";
import type {
    LibraryDatasetUploadItem,
    LocalFileUploadItem,
    PastedContentUploadItem,
    RemoteFileUploadItem,
    UrlUploadItem,
} from "@/composables/upload/uploadItemTypes";

export function makePastedItem(overrides: Partial<PastedContentUploadItem> = {}): PastedContentUploadItem {
    return {
        uploadMode: "paste-content",
        name: "file.txt",
        content: "hello world",
        size: 11,
        targetHistoryId: "hist_1",
        dbkey: "?",
        extension: "auto",
        spaceToTab: false,
        toPosixLines: false,
        deferred: false,
        ...overrides,
    };
}

export function makeUrlItem(overrides: Partial<UrlUploadItem> = {}): UrlUploadItem {
    return {
        uploadMode: "paste-links",
        name: "file.txt",
        url: "http://example.com/file.txt",
        size: 0,
        targetHistoryId: "hist_1",
        dbkey: "?",
        extension: "auto",
        spaceToTab: false,
        toPosixLines: false,
        deferred: false,
        ...overrides,
    };
}

export function makeRemoteFilesItem(overrides: Partial<RemoteFileUploadItem> = {}): RemoteFileUploadItem {
    return {
        uploadMode: "remote-files",
        name: "file.txt",
        url: "ftp://server/file.txt",
        size: 0,
        targetHistoryId: "hist_1",
        dbkey: "?",
        extension: "auto",
        spaceToTab: false,
        toPosixLines: false,
        deferred: false,
        ...overrides,
    };
}

export function makeLibraryItem(overrides: Partial<LibraryDatasetUploadItem> = {}): LibraryDatasetUploadItem {
    return {
        uploadMode: "data-library",
        name: "library.txt",
        size: 0,
        targetHistoryId: "hist_1",
        dbkey: "?",
        extension: "auto",
        spaceToTab: false,
        toPosixLines: false,
        deferred: false,
        libraryId: "lib_1",
        folderId: "folder_1",
        lddaId: "ldda_1",
        url: "/api/libraries/lib_1/datasets/ldda_1",
        ...overrides,
    };
}

export function makeLocalFileItem(overrides: Partial<LocalFileUploadItem> = {}): LocalFileUploadItem {
    const file = new File(["content"], "test.txt");
    return {
        uploadMode: "local-file",
        name: "test.txt",
        size: file.size,
        targetHistoryId: "hist_1",
        dbkey: "?",
        extension: "auto",
        spaceToTab: false,
        toPosixLines: false,
        deferred: false,
        fileData: file,
        ...overrides,
    };
}

export function makeCollectionConfig(overrides: Partial<UploadCollectionConfig> = {}): UploadCollectionConfig {
    return {
        name: "My Collection",
        type: "list",
        historyId: "hist_1",
        hideSourceItems: false,
        ...overrides,
    };
}
