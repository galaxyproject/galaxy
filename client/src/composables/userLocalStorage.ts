import { watchImmediate } from "@vueuse/core";
import { type Ref, ref } from "vue";

import { type AnyUser } from "@/api";

import { useHashedUserId } from "./hashedUserId";
import { syncRefToLocalStorage } from "./persistentRef";

/**
 * Local storage composable specific to current user.
 * @param key
 * @param initialValue
 */
export function useUserLocalStorage<T>(key: string, initialValue: T, user?: Ref<AnyUser>) {
    const { hashedUserId } = useHashedUserId(user);

    const refToSync = ref(initialValue);
    let hasSynced = false;

    watchImmediate(
        () => hashedUserId.value,
        () => {
            if (hashedUserId.value && !hasSynced) {
                syncRefToLocalStorage(`${key}-${hashedUserId.value}`, refToSync);
                hasSynced = true;
            }
        }
    );

    return refToSync;
}
