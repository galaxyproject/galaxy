import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import type { CompositeFileInfo } from "@/api/datatypes";
import { AUTO_EXTENSION, DEFAULT_EXTENSION, getUploadDatatypes, getUploadDbKeys } from "@/components/Upload/utils";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";

import { useConfig } from "./config";

type ExtensionDetails = {
    id: string;
    text: string;
    description: string | null;
    description_url: string | null;
    composite_files?: CompositeFileInfo[] | null;
    upload_warning?: string | null;
};

export function useUploadConfigurations(extensions: string[] | undefined) {
    const { config, isConfigLoaded } = useConfig();

    extensions = extensions?.filter((ext) => ext !== "data");

    const configOptions = computed(() =>
        isConfigLoaded.value
            ? {
                  chunkUploadSize: config.value.chunk_upload_size,
                  fileSourcesConfigured: config.value.file_sources_configured,
                  ftpUploadSite: config.value.ftp_upload_site,
                  defaultDbKey: config.value.default_genome || "",
                  defaultExtension: extensions?.length
                      ? extensions[0]
                      : config.value.default_extension || DEFAULT_EXTENSION,
              }
            : {}
    );

    // Load the list of extensions
    // TODO: Maybe a store would be better for this
    const listExtensions = ref<ExtensionDetails[]>([]);
    const extensionsSet = ref(false);
    async function loadExtensions() {
        listExtensions.value = await getUploadDatatypes(false, AUTO_EXTENSION);
        extensionsSet.value = true;
    }
    loadExtensions();

    const datatypesMapperStore = useDatatypesMapperStore();
    const { datatypesMapper, loading: datatypesMapperLoading } = storeToRefs(datatypesMapperStore);
    datatypesMapperStore.createMapper();

    const effectiveExtensions = computed(() => {
        if (extensions?.length && datatypesMapper.value && !datatypesMapperLoading.value) {
            const result: ExtensionDetails[] = [];
            listExtensions.value.forEach((extension) => {
                if (extension && extension.id == DEFAULT_EXTENSION) {
                    result.push(extension);
                } else if (datatypesMapper.value?.isSubTypeOfAny(extension.id, extensions!)) {
                    result.push(extension);
                }
            });
            return result;
        } else {
            return listExtensions.value;
        }
    });

    const listDbKeys = ref<{ id: string; text: string }[]>([]);
    const dbKeysSet = ref(false);
    async function loadDbKeys() {
        listDbKeys.value = await getUploadDbKeys(config.value?.default_genome || "");
        dbKeysSet.value = true;
    }

    watch(
        () => config.value,
        async (c) => {
            if (c) {
                await loadDbKeys();
            }
        },
        { immediate: true }
    );

    const ready = computed(
        () => dbKeysSet.value && extensionsSet.value && !!datatypesMapper.value && !datatypesMapperLoading.value
    );

    return {
        configOptions,
        effectiveExtensions,
        listDbKeys,
        ready,
    };
}
