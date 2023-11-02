import { type Ref, ref, watch } from "vue";

interface ToggleStateInterface {
    toggled: Ref<boolean>;
    toggle: () => void;
}

export function usePersistentToggle(uniqueId: string): ToggleStateInterface{
    const localStorageKey = `toggle-state-${uniqueId}`;

    // Retrieve the toggled state from localStorage if available, otherwise default to false
    const toggled = ref<boolean>(localStorage.getItem(localStorageKey) === "true");

    // Watch for changes in the toggled state and persist them to localStorage
    watch(toggled, (newVal: boolean) => {
        localStorage.setItem(localStorageKey, String(newVal));
    });

    // Expose a function for toggling state
    const toggle = () => {
        toggled.value = !toggled.value;
    };

    return {
        toggled,
        toggle,
    };
}
