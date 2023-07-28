import type { components } from "@/schema";
import { fetcher } from "@/schema/fetcher";

export type FilesSourcePlugin = components["schemas"]["FilesSourcePlugin"];
export type RemoteFile = components["schemas"]["RemoteFile"];
export type RemoteDirectory = components["schemas"]["RemoteDirectory"];
export type RemoteEntry = RemoteFile | RemoteDirectory;
export type CreatedEntry = components["schemas"]["CreatedEntryResponse"];

const getRemoteFilesPlugins = fetcher.path("/api/remote_files/plugins").method("get").create();

/**
 * Get the list of available file sources from the server that can be browsed.
 * @param rdm_only Whether to only include Research Data Management (RDM) specific file sources.
 * @returns The list of available file sources from the server.
 */
export async function getFileSources(rdm_only = false): Promise<FilesSourcePlugin[]> {
    const { data } = await getRemoteFilesPlugins({ browsable_only: true, rdm_only: rdm_only });
    return data;
}

const getRemoteFiles = fetcher.path("/api/remote_files").method("get").create();

/**
 * Get the list of files and directories from the server for the given file source URI.
 * @param uri The file source URI to browse.
 * @param isRecursive Whether to recursively retrieve all files inside subdirectories.
 * @param writeable Whether to return only entries that can be written to.
 * @returns The list of files and directories from the server for the given URI.
 */
export async function browseRemoteFiles(uri: string, isRecursive = false, writeable = false): Promise<RemoteEntry[]> {
    const { data } = await getRemoteFiles({ target: uri, recursive: isRecursive, writeable });
    return data as RemoteEntry[];
}

const createEntry = fetcher.path("/api/remote_files").method("post").create();

/**
 * Create a new entry (directory/record) on the given file source URI.
 * @param uri The file source URI to create the entry in.
 * @param name The name of the entry to create.
 * @returns The created entry details.
 */
export async function createRemoteEntry(uri: string, name: string): Promise<CreatedEntry> {
    const { data } = await createEntry({ target: uri, name: name });
    return data;
}
