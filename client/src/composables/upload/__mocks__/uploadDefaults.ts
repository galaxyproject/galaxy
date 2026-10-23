import { ref } from "vue";

// Opt in per file with `vi.mock("@/composables/upload/uploadDefaults")`.
export function useUploadDefaults() {
    return {
        effectiveExtensions: ref([]),
        listDbKeys: ref([]),
        configurationsReady: ref(true),
        createItemDefaults: () => ({
            extension: "auto",
            dbkey: "?",
            spaceToTab: false,
            toPosixLines: false,
            autoDecompress: true,
        }),
    };
}
