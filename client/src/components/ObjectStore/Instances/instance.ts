import { computed, type Ref } from "vue";

import { type ObjectStoreTemplateSummary } from "@/components/ObjectStore/Templates/types";
import { useObjectStoreInstancesStore } from "@/stores/objectStoreInstancesStore";
import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";

import { type UserConcreteObjectStore } from "./types";

export function useInstanceAndTemplate(instanceIdRef: Ref<string>) {
    const objectStoreTemplatesStore = useObjectStoreTemplatesStore();
    const objectStoreInstancesStore = useObjectStoreInstancesStore();
    objectStoreInstancesStore.fetchInstances();
    objectStoreTemplatesStore.fetchTemplates();

    const instance = computed<UserConcreteObjectStore | null>(
        () => objectStoreInstancesStore.getInstance(instanceIdRef.value) || null
    );
    const template = computed<ObjectStoreTemplateSummary | null>(() =>
        instance.value
            ? objectStoreTemplatesStore.getTemplate(instance.value?.template_id, instance.value?.template_version)
            : null
    );

    return { instance, template };
}
