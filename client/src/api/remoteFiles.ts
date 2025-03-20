import { type components, GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

/** The browsing mode:
 * - `file` - allows to select files or directories contained in a source (default)
 * - `directory` - allows to select directories (paths) only
 * - `source` - allows to select a source plugin root and doesn't list its contents
 */
export type FileSourceBrowsingMode = "file" | "directory" | "source";
export type FilesSourcePlugin = components["schemas"]["FilesSourcePlugin"];
export type BrowsableFilesSourcePlugin = components["schemas"]["BrowsableFilesSourcePlugin"];
export type RemoteFile = components["schemas"]["RemoteFile"];
export type RemoteDirectory = components["schemas"]["RemoteDirectory"];
export type RemoteEntry = RemoteFile | RemoteDirectory;
export type CreatedEntry = components["schemas"]["CreatedEntryResponse"];
export type FileSourcePluginKind = components["schemas"]["PluginKind"];

/** The options to filter the list of available file sources. */
export interface FilterFileSourcesOptions {
    /** The kinds of file sources to return, multiple kinds can be specified.
     * If undefined, all file sources are returned.
     */
    include?: FileSourcePluginKind[];
    /** The kind of file sources to exclude, multiple kinds can be specified.
     * Excluded have precedence over included.
     * If undefined, all file sources are returned.
     */
    exclude?: FileSourcePluginKind[];
}

/**
 * Get the list of available file sources from the server that can be browsed.
 * @param options The options to filter the file sources.
 * @returns The list of available (browsable) file sources from the server.
 */
export async function fetchFileSources(options: FilterFileSourcesOptions = {}): Promise<BrowsableFilesSourcePlugin[]> {
    const { data, error } = await GalaxyApi().GET("/api/remote_files/plugins", {
        params: {
            query: {
                browsable_only: true,
                include_kind: options.include,
                exclude_kind: options.exclude,
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    // Since we specified browsable_only in the query, we can safely cast the data to the expected type.
    return data as BrowsableFilesSourcePlugin[];
}

export interface BrowseRemoteFilesResult {
    entries: RemoteEntry[];
    totalMatches: number;
}

/**
 * Get the list of files and directories from the server for the given file source URI.
 * @param uri The file source URI to browse.
 * @param isRecursive Whether to recursively retrieve all files inside subdirectories.
 * @param writeable Whether to return only entries that can be written to.
 * @param limit The maximum number of entries to return.
 * @param offset The number of entries to skip before returning the rest.
 * @param query The query string to filter the entries.
 * @param sortBy The field to sort the entries by.
 * @returns The list of files and directories from the server for the given URI.
 */
export async function browseRemoteFiles(
    uri: string,
    isRecursive = false,
    writeable = false,
    limit?: number,
    offset?: number,
    query?: string,
    sortBy?: string
): Promise<BrowseRemoteFilesResult> {
    const { response, data, error } = await GalaxyApi().GET("/api/remote_files", {
        params: {
            query: {
                format: "uri",
                target: uri,
                recursive: isRecursive,
                writeable,
                limit,
                offset,
                query,
                sort_by: sortBy,
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    const totalMatches = parseInt(response.headers.get("total_matches") ?? "0");

    // Since we specified format=uri in the query, we can safely cast the data to the expected type.
    const entries = data as RemoteEntry[];
    return { entries, totalMatches };
}
