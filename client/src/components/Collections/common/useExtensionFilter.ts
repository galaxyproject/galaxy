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
    const filterExtensions = computed(() => !!datatypesMapper.value && extensions.value && extensions.value.length > 0);

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

    /** Show the element's extension next to its name:
     *  1. If there are no required extensions, so users can avoid creating mixed extension lists.
     *  2. If the extension is not in the list of required extensions but is a subtype of one of them,
     *     so users can see that those elements were still included as they can be interpreted as the subtype.
     */
    function showElementExtension(element: ElementHasExtension) {
        return (
            !props.extensions?.length ||
            (filterExtensions.value &&
                element.extension &&
                !props.extensions?.includes(element.extension) &&
                datatypesMapper.value?.isSubTypeOfAny(element.extension, props.extensions!))
        );
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
        showElementExtension,
    };
}
