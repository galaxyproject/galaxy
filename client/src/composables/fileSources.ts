import { onMounted, readonly, ref } from "vue";

import { FilesSourcePlugin, getFileSources } from "@/components/FilesDialog/services";

/**
 * Composable for accessing and working with file sources.
 */
export function useFileSources() {
    const isLoading = ref(true);
    const hasWritable = ref(false);
    const fileSources = ref<FilesSourcePlugin[]>([]);

    onMounted(async () => {
        fileSources.value = await getFileSources();
        hasWritable.value = fileSources.value.some((fs) => fs.writable);
        isLoading.value = false;
    });

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
    };
}
