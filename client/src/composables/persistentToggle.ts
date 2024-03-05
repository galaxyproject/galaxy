import { type Ref } from "vue";

import { useUserLocalStorage } from "./userLocalStorage";

interface ToggleStateInterface {
    toggled: Ref<boolean>;
    toggle: () => void;
}

export function usePersistentToggle(uniqueId: string): ToggleStateInterface {
    const localStorageKey = `toggle-state-${uniqueId}`;
    const toggled = useUserLocalStorage(localStorageKey, false);

    // Expose a function for toggling state
    const toggle = () => {
        toggled.value = !toggled.value;
    };

    return {
        toggled,
        toggle,
    };
}
