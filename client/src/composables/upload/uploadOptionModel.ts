import type { UploadOptionVisibility } from "@/components/Panels/Upload/shared/uploadOptionVisibility";

export type UploadOptionKey = "spaceToTab" | "toPosixLines" | "deferred" | "autoDecompress";

export interface UploadOptionDefinition {
    key: UploadOptionKey;
    visibilityKey: keyof UploadOptionVisibility;
    label: string;
    headerTooltip: string;
    rowTooltip: string;
    defaultValue: boolean;
}

export const uploadOptionDefinitions: UploadOptionDefinition[] = [
    {
        key: "spaceToTab",
        visibilityKey: "spaceToTab",
        label: "Spaces→Tabs",
        headerTooltip: "Toggle all: Convert spaces to tab characters",
        rowTooltip: "Convert spaces to tab characters",
        defaultValue: false,
    },
    {
        key: "toPosixLines",
        visibilityKey: "posix",
        label: "POSIX",
        headerTooltip: "Toggle all: Convert line endings to POSIX standard",
        rowTooltip: "Convert line endings to POSIX standard",
        defaultValue: false,
    },
    {
        key: "deferred",
        visibilityKey: "deferred",
        label: "Deferred",
        headerTooltip: "Toggle all: Galaxy will store a reference and fetch data only when needed by a tool",
        rowTooltip: "Galaxy will store a reference and fetch data only when needed by a tool",
        defaultValue: false,
    },
    {
        key: "autoDecompress",
        visibilityKey: "autoDecompress",
        label: "Auto-decompress",
        headerTooltip: "Toggle all: Disable automatic decompression of compressed inputs",
        rowTooltip: "Automatic decompression of compressed inputs after upload",
        defaultValue: true,
    },
];

export const uploadOptionDefinitionByKey: Record<UploadOptionKey, UploadOptionDefinition> =
    uploadOptionDefinitions.reduce(
        (acc, definition) => {
            acc[definition.key] = definition;
            return acc;
        },
        {} as Record<UploadOptionKey, UploadOptionDefinition>,
    );

export function isUploadOptionVisible(key: UploadOptionKey, visibility: UploadOptionVisibility): boolean {
    const definition = uploadOptionDefinitionByKey[key];
    return visibility[definition.visibilityKey];
}

export const uploadOptionDefaults = {
    spaceToTab: uploadOptionDefinitions.find((option) => option.key === "spaceToTab")?.defaultValue ?? false,
    toPosixLines: uploadOptionDefinitions.find((option) => option.key === "toPosixLines")?.defaultValue ?? false,
    deferred: uploadOptionDefinitions.find((option) => option.key === "deferred")?.defaultValue ?? false,
    autoDecompress: uploadOptionDefinitions.find((option) => option.key === "autoDecompress")?.defaultValue ?? true,
} as const;

export const uploadApiOptionDefaults = {
    space_to_tab: uploadOptionDefaults.spaceToTab,
    to_posix_lines: uploadOptionDefaults.toPosixLines,
    deferred: uploadOptionDefaults.deferred,
    auto_decompress: uploadOptionDefaults.autoDecompress,
} as const;
