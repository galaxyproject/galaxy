import type { components } from "@/schema";
import { fetcher } from "@/schema/fetcher";

export type FilesSourcePlugin = components["schemas"]["FilesSourcePlugin"];

const getRemoteFilesPlugins = fetcher.path("/api/remote_files/plugins").method("get").create();

export async function getFileSources(): Promise<FilesSourcePlugin[]> {
    const { data } = await getRemoteFilesPlugins({ browsable_only: true });
    return data;
}

const getRemoteFiles = fetcher.path("/api/remote_files").method("get").create();

export async function browseRemoteFiles(uri: string, isRecursive = false) {
    const { data } = await getRemoteFiles({ target: uri, recursive: isRecursive });
    return data;
}
