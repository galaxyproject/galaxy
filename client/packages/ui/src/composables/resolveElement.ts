import { computed, type Ref } from "vue";

export function useResolveElement(elementRef: Ref<unknown>) {
    const resolvedRef = computed(() => {
        const value = elementRef.value;

        if (typeof value === "object" && value !== null && "$el" in value) {
            return value.$el as HTMLElement;
        } else {
            return value as HTMLElement | null;
        }
    });

    return resolvedRef;
}
