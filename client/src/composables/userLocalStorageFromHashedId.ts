import { watchImmediate } from "@vueuse/core";
import { type Ref, ref, type UnwrapRef } from "vue";

import { syncRefToLocalStorage } from "./persistentRef";

/**
 * Local storage composable specific to current user.
 * @param key
 * @param initialValue
 */
export function useUserLocalStorageFromHashId<T>(
    key: string,
    initialValue: T,
    hashedUserId: Ref<string | null>
): Ref<UnwrapRef<T>> {
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
