import { createPinia, setActivePinia } from "pinia";

export function setupTestPinia() {
    setActivePinia(createPinia());
}
