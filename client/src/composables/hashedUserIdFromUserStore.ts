import { storeToRefs } from "pinia";

import { useUserStore } from "@/stores/userStore";

import { useHashedUserId as parentUseHashedUserId } from "./hashedUserId";

/**
 * One way hashed ID of the current User
 */
export function useHashedUserId() {
    const { currentUser: currentUserRef } = storeToRefs(useUserStore());
    return parentUseHashedUserId(currentUserRef);
}
