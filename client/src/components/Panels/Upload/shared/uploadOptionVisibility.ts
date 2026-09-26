export interface UploadOptionVisibility {
    spaceToTab: boolean;
    posix: boolean;
    deferred: boolean;
    autoDecompress: boolean;
}

export const defaultUploadOptionVisibility: UploadOptionVisibility = {
    spaceToTab: false,
    posix: false,
    deferred: false,
    autoDecompress: false,
};

export function localUploadOptionVisibility(advancedMode: boolean): UploadOptionVisibility {
    return {
        spaceToTab: true,
        posix: advancedMode,
        deferred: false,
        autoDecompress: advancedMode,
    };
}

export function urlUploadOptionVisibility(advancedMode: boolean): UploadOptionVisibility {
    return {
        spaceToTab: true,
        posix: advancedMode,
        deferred: true,
        autoDecompress: advancedMode,
    };
}
