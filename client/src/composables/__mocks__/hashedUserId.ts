import { computed } from "vue";

// set to always mock in tests/vitest/setup.ts
export function useHashedUserId() {
    const hashedUserId = computed(() => "fake-hashed-id");

    return { hashedUserId };
}
