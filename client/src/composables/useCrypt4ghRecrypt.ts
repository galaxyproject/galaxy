import axios from "axios";
import { ref } from "vue";

import type { HDADetailed } from "@/api";
import { setAttributes } from "@/components/DatasetInformation/services";
import { Toast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString } from "@/utils/simple-error";

/** Keys that the recryptor service returns in its response. */
interface RecryptServiceResponse {
    crypt4gh_header: string;
    crypt4gh_compute_keypair_id: string;
    crypt4gh_compute_keypair_expiration_date: string;
}

/** Fields sent to `setAttributes` to persist compute re-encryption metadata. */
type Crypt4ghComputeAttributes = {
    crypt4gh_compute_header: string;
    crypt4gh_compute_keypair_id: string;
    crypt4gh_compute_keypair_expiration_date: string;
};

/**
 * Extracts the `metadata_crypt4gh_header` field from a dataset.
 */
function getCrypt4ghHeader(item: HDADetailed): string | undefined {
    return (item as unknown as Record<string, unknown>)["metadata_crypt4gh_header"] as string | undefined;
}

/**
 * Extracts the Crypt4GH recrypt service URL from the user's extra preferences.
 *
 * The port is stored under the `crypt4gh_recrypt_service|port` key inside the
 * `extra_user_preferences` JSON string in the user store.
 */
function getRecryptServiceUrl(): string {
    const userStore = useUserStore();
    const prefs = userStore.currentPreferences as Record<string, unknown> | null;
    const extraPrefsRaw = prefs?.["extra_user_preferences"];

    if (!extraPrefsRaw || typeof extraPrefsRaw !== "string") {
        throw new Error("No Crypt4GH recrypt service configured. Set the port in your user preferences.");
    }

    const extraPrefs = JSON.parse(extraPrefsRaw) as Record<string, string>;
    const port = extraPrefs["crypt4gh_recrypt_service|port"];

    if (!port) {
        throw new Error("No Crypt4GH recrypt service port configured. Set the port in your user preferences.");
    }

    return `https://localhost:${port}/recrypt_header`;
}

/**
 * Calls the external recryptor service to re-encrypt a Crypt4GH header for
 * compute use. Returns the compute header and keypair metadata.
 */
async function fetchRecryptedHeader(crypt4ghHeader: string): Promise<Crypt4ghComputeAttributes> {
    const serviceUrl = getRecryptServiceUrl();
    const { data } = await axios.post<RecryptServiceResponse>(serviceUrl, {
        crypt4gh_header: crypt4ghHeader,
    });

    return {
        crypt4gh_compute_header: data.crypt4gh_header,
        crypt4gh_compute_keypair_id: data.crypt4gh_compute_keypair_id,
        crypt4gh_compute_keypair_expiration_date: data.crypt4gh_compute_keypair_expiration_date,
    };
}

/**
 * Composable that provides Crypt4GH recrypt functionality for a dataset.
 *
 * Encapsulates the full recrypt flow:
 * 1. Read the stored Crypt4GH header from dataset metadata.
 * 2. Call the external recryptor service to produce a compute header.
 * 3. Persist the compute metadata via `setAttributes`.
 * 4. Reload the current history so the UI reflects the new state.
 *
 * Exposes a `recrypting` ref for loading-state binding and a `recrypt` method
 * that performs the operation with built-in error handling and toast feedback.
 */
export function useCrypt4ghRecrypt() {
    const recrypting = ref(false);

    async function recrypt(item: HDADetailed) {
        if (recrypting.value) {
            return;
        }

        const crypt4ghHeader = getCrypt4ghHeader(item);
        if (!crypt4ghHeader) {
            Toast.error("Dataset does not have a stored Crypt4GH header.", "Recrypt failed");
            return;
        }

        recrypting.value = true;
        try {
            const computeAttributes = await fetchRecryptedHeader(crypt4ghHeader);

            await setAttributes(
                item.id,
                {
                    name: item.name,
                    info: item.misc_info ?? "",
                    ...computeAttributes,
                },
                "attributes",
            );

            const historyStore = useHistoryStore();
            await historyStore.loadCurrentHistory();

            Toast.success("Crypt4GH header re-encrypted for compute.");
        } catch (err) {
            Toast.error(errorMessageAsString(err, "Crypt4GH recrypt failed."), "Recrypt failed");
        } finally {
            recrypting.value = false;
        }
    }

    return { recrypting, recrypt };
}
