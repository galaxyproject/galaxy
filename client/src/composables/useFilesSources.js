import { computed, onMounted, reactive, toRefs } from "vue";
import { Services } from "components/FilesDialog/services";

const state = reactive({
    initializingFileSources: true,
    fileSources: [],
});

/**
 * Reusable functionality around Files Sources plugins.
 *
 * TODO: this should replace exportsMixin.js at some point
 *
 * @returns Exposed properties and functions
 */
export function useFilesSources() {
    const writableFileSources = computed(() => state.fileSources.filter((fs) => fs.writable));

    //TODO: use store?
    async function initializeFileSources() {
        if (!state.fileSources.length) {
            state.fileSources = await new Services().getFileSources();
            state.initializingFileSources = false;
        }
    }

    onMounted(() => {
        initializeFileSources();
    });
    return { ...toRefs(state), writableFileSources };
}
