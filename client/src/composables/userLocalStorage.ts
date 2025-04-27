import { type Ref, type UnwrapRef } from "vue";

import { type AnyUser } from "@/api";

import { useHashedUserId } from "./hashedUserId";
import { useHashedUserId as useHashedUserIdFromStore } from "./hashedUserIdFromUserStore";
import { useUserLocalStorageFromHashId } from "./userLocalStorageFromHashedId";

/**
 * Local storage composable specific to current user.
 * @param key
 * @param initialValue
 */
export function useUserLocalStorage<T>(key: string, initialValue: T, user?: Ref<AnyUser>): Ref<UnwrapRef<T>> {
    let hashedUserId;
    if (user) {
        hashedUserId = useHashedUserId(user).hashedUserId;
    } else {
        hashedUserId = useHashedUserIdFromStore().hashedUserId;
    }
    return useUserLocalStorageFromHashId<T>(key, initialValue, hashedUserId);
}
