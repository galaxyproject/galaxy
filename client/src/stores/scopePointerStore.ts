import { defineStore } from "pinia";
import { computed, ref } from "vue";

/**
 * This store allows for pointing scoped stores to other scoped stores
 */
export const useScopePointerStore = defineStore("scopePointerStore", () => {
    type FromScopeId = string;
    type ToScopeId = string;

    const scopePointers = ref<Record<FromScopeId, ToScopeId | undefined>>({});

    function addScopePointer(from: FromScopeId, to: ToScopeId) {
        scopePointers.value[from] = scope.value(to);
    }

    const scope = computed(() => (scopeId: string) => scopePointers.value[scopeId] ?? scopeId);

    function removeScopePointer(id: FromScopeId) {
        scopePointers.value[id] = undefined;
    }

    return {
        addScopePointer,
        removeScopePointer,
        scope,
    };
});
