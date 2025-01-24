import { onMounted, readonly, ref } from "vue";

import { type BrowsableFilesSourcePlugin, type FilterFileSourcesOptions } from "@/api/remoteFiles";
import { useFileSourcesStore } from "@/stores/fileSourcesStore";

/**
 * Composable for accessing and working with file sources.
 *
 * @param options - The options to filter the file sources.
 */
export function useFileSources(options: FilterFileSourcesOptions = {}) {
    const fileSourcesStore = useFileSourcesStore();

    const isLoading = ref(true);
    const hasWritable = ref(false);
    const fileSources = ref<BrowsableFilesSourcePlugin[]>([]);

    onMounted(async () => {
        fileSources.value = await fileSourcesStore.getFileSources(options);
        hasWritable.value = fileSources.value.some((fs) => fs.writable);
        isLoading.value = false;
    });

    function getFileSourceById(id: string) {
        return fileSources.value.find((fs) => fs.id === id);
    }

    function getFileSourceByUri(uri: string) {
        const sourceId = getFileSourceIdFromUri(uri);
        let matchedFileSource = getFileSourceById(sourceId);
        if (matchedFileSource) {
            return matchedFileSource;
        }

        // Match by URI root if the source ID is not found.
        matchedFileSource = fileSources.value.find((fs) => uri.startsWith(fs.uri_root));
        return matchedFileSource;
    }

    function getFileSourceIdFromUri(uri: string) {
        const sourceId = uri.split("://")[1]?.split("/")[0] ?? "";
        return sourceId;
    }

    return {
        /**
         * The list of available file sources from the server.
         */
        fileSources: readonly(fileSources),
        /**
         * Whether the file sources are being loaded from the server.
         */
        isLoading: readonly(isLoading),
        /**
         * Whether the user can write files to any of the available file sources.
         */
        hasWritable: readonly(hasWritable),
        /**
         * Get the file source with the given ID.
         *
         * @param id - The ID of the file source to get.
         * @returns The file source with the given ID, if found.
         */
        getFileSourceById,
        /**
         * Get the file source that matches the given URI.
         *
         * @param uri - The URI to match.
         * @returns The file source that matches the given URI, if found.
         */
        getFileSourceByUri,
    };
}
