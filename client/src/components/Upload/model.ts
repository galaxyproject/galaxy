export interface UploadFile {
    mode: string | null;
    name: string | null;
    size: number | null;
    uri?: string | null;
    path?: string | null;
    label?: string | null;
    url?: string | null;
}

export interface UploadItem {
    dbKey: string;
    deferred: boolean;
    enabled: boolean;
    extension: string;
    fileContent: string;
    fileData: object | null;
    fileMode: string;
    fileName: string;
    filePath: string;
    fileSize: number;
    fileUri?: string | null;
    info?: string | null;
    optional: boolean;
    outputs: object | null;
    percentage: number;
    spaceToTab: boolean;
    status: string;
    targetHistoryId?: string;
    toPosixLines: boolean;
    id?: string;
}

export const defaultModel: UploadItem = {
    dbKey: "?",
    deferred: false,
    enabled: true,
    extension: "auto",
    fileContent: "",
    fileData: null,
    fileMode: "",
    fileName: "",
    filePath: "",
    fileSize: 0,
    fileUri: null,
    info: null,
    optional: false,
    outputs: null,
    percentage: 0,
    spaceToTab: false,
    status: "init",
    toPosixLines: true,
};
