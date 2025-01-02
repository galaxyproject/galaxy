import { computed, toRef, watch } from "vue";

import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";

interface PropsWithOptionalExtensions {
    extensions?: string[];
}

interface ElementHasExtension {
    extension: string | null | undefined;
}

export function useExtensionFiltering(props: PropsWithOptionalExtensions) {
    const extensions = toRef(props, "extensions");
    // variables for datatype mapping and then filtering
    const datatypesMapperStore = useDatatypesMapperStore();
    const datatypesMapper = computed(() => datatypesMapperStore.datatypesMapper);
    const filterExtensions = computed(() => !!datatypesMapper.value && !!extensions.value);

    function hasInvalidExtension(element: ElementHasExtension) {
        if (
            filterExtensions.value &&
            element.extension &&
            !datatypesMapper.value?.isSubTypeOfAny(element.extension, props.extensions!)
        ) {
            return true;
        } else {
            return false;
        }
    }

    watch(
        () => datatypesMapper.value,
        async (mapper) => {
            if (extensions.value?.length && !mapper) {
                await datatypesMapperStore.createMapper();
            }
        },
        { immediate: true }
    );

    return {
        hasInvalidExtension,
    };
}
