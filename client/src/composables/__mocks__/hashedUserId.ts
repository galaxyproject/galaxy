import { computed } from "vue";

// set to always mock in jest.setup.js
export function useHashedUserId() {
    const hashedUserId = computed(() => "fake-hashed-id");

    return { hashedUserId };
}
