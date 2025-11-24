import { ref } from "vue";

// set to always mock in tests/vitest/setup.ts
export function useUserLocalStorage<T>(_key: string, initialValue: T) {
    return ref(initialValue);
}
