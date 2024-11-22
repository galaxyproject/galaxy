import { computed, type Ref, ref } from "vue";

import { type AnyUser } from "@/api";

import { useHashedUserId } from "./hashedUserId";
import { usePersistentRef } from "./persistentRef";

/**
 * Local storage composable specific to current user.
 * @param key
 * @param initialValue
 */
export function useUserLocalStorage<T>(key: string, initialValue: T, user?: Ref<AnyUser>) {
    const { hashedUserId } = useHashedUserId(user);

    const storedRef = computed(() => {
        if (hashedUserId.value) {
            return usePersistentRef(`${key}-${hashedUserId.value}`, initialValue);
        } else {
            return ref(initialValue);
        }
    });

    const currentValue = computed({
        get() {
            return storedRef.value.value;
        },
        set(newValue) {
            storedRef.value.value = newValue;
        },
    });

    return currentValue;
}
