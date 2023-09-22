import { computed, ref, watch } from "vue";
import { useCurrentUser } from "./user";
import { useLocalStorage } from "@vueuse/core";

async function hash32(value: string): Promise<string> {
    const valueUtf8 = new TextEncoder().encode(value);
    const hashBuffer = await crypto.subtle.digest("SHA-256", valueUtf8);

    return bufferToString(hashBuffer);
}

function bufferToString(buffer: ArrayBuffer): string {
    const u8Array = new Uint8Array(buffer);
    const hashString = window.btoa(String.fromCharCode(...u8Array));

    return hashString;
}

function createSalt(): string {
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);

    return bufferToString(bytes);
}

const currentHash = ref<string | null>(null);
let unhashedId: string | null = null;

/**
 * One way hashed ID of the current User
 */
export function useHashedUserId() {
    const { currentUser } = useCurrentUser(true);

    // salt the local store, to make a user untraceable by id across different clients
    const localStorageSalt = useLocalStorage("local-storage-salt", createSalt());

    watch(
        () => currentUser.value,
        () => {
            if (currentUser.value && !currentUser.value.isAnonymous) {
                hashUserId(currentUser.value.id + localStorageSalt.value);
            }
        },
        {
            immediate: true,
        }
    );

    async function hashUserId(id: string) {
        if (unhashedId !== id) {
            unhashedId = id;
            currentHash.value = null;

            const hashed = await hash32(id);

            currentHash.value = hashed;
        }
    }

    const hashedUserId = computed(() => currentHash.value);

    return { hashedUserId };
}
