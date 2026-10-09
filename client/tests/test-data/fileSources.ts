import type { BrowsableFilesSourcePlugin } from "@/api/remoteFiles";

type FileSourceOverrides = Partial<Omit<BrowsableFilesSourcePlugin, "supports">> & {
    supports?: Partial<BrowsableFilesSourcePlugin["supports"]>;
};

export function getFakeFileSource(overrides: FileSourceOverrides = {}): BrowsableFilesSourcePlugin {
    const id = overrides.id ?? "file-source-id";
    return {
        id,
        type: "posix",
        uri_root: `gxfiles://${id}`,
        label: "Test File Source",
        doc: "Test File Source Description",
        writable: true,
        browsable: true,
        ...overrides,
        supports: {
            pagination: false,
            search: false,
            sorting: false,
            ...overrides.supports,
        },
    };
}
