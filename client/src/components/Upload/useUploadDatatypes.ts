import { ref } from "vue";

import type { CompositeFileInfo } from "@/api/datatypes";
import { AUTO_EXTENSION, getUploadDatatypes } from "@/components/Upload/utils";

type ExtensionDetails = {
    id: string;
    text: string;
    description: string | null;
    description_url: string | null;
    composite_files?: CompositeFileInfo[] | null;
    upload_warning?: string | null;
};

export function useUploadDatatypes() {
    const listExtensions = ref<ExtensionDetails[]>([]);
    const extensionsSet = ref(false);

    async function loadExtensions() {
        listExtensions.value = await getUploadDatatypes(false, AUTO_EXTENSION);
        extensionsSet.value = true;
    }

    return {
        listExtensions,
        extensionsSet,
        loadExtensions,
    };
}
