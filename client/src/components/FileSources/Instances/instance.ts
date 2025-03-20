import { computed, type Ref } from "vue";

import { type FileSourceTemplateSummary, type UserFileSourceModel } from "@/api/fileSources";
import { useFileSourceInstancesStore } from "@/stores/fileSourceInstancesStore";
import { useFileSourceTemplatesStore } from "@/stores/fileSourceTemplatesStore";

export function useInstanceAndTemplate(instanceIdRef: Ref<string>) {
    const fileSourceTemplatesStore = useFileSourceTemplatesStore();
    const fileSourceInstancesStore = useFileSourceInstancesStore();
    fileSourceInstancesStore.fetchInstances();
    fileSourceTemplatesStore.fetchTemplates();

    const instance = computed<UserFileSourceModel | null>(
        () => fileSourceInstancesStore.getInstance(instanceIdRef.value) || null
    );
    const template = computed<FileSourceTemplateSummary | null>(() =>
        instance.value
            ? fileSourceTemplatesStore.getTemplate(instance.value?.template_id, instance.value?.template_version)
            : null
    );

    return { instance, template };
}
