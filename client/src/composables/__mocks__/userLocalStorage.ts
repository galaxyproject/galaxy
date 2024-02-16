import { ref } from "vue";

// set to always mock in jest.setup.js
export function useUserLocalStorage<T>(_key: string, initialValue: T) {
    return ref(initialValue);
}
