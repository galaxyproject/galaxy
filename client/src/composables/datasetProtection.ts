import axios from "axios";
import { type Ref, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import type { components } from "@/api/schema";
import { Toast } from "@/composables/toast";
import { useConfigStore } from "@/stores/configurationStore";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString, rethrowSimple } from "@/utils/simple-error";

export type DatasetProtectionStatus = components["schemas"]["DatasetProtectionStatus"];

/** Response of the user-side recryptor service (`POST /recrypt_header`). */
interface RecryptServiceResponse {
    crypt4gh_header: string;
    crypt4gh_compute_keypair_id: string;
    crypt4gh_compute_keypair_expiration_date: string;
}

const RECRYPT_SERVICE_PORT_PREFERENCE = "crypt4gh_recrypt_service|port";

/**
 * URL of the user-side recryptor service. The port can be overridden in the
 * user's extra preferences when the admin configured that preference.
 */
export function getRecryptServiceUrl(serviceUrl: string, extraPreferences: unknown): string {
    const url = new URL(serviceUrl);
    if (typeof extraPreferences === "string" && extraPreferences) {
        const port = (JSON.parse(extraPreferences) as Record<string, string>)[RECRYPT_SERVICE_PORT_PREFERENCE];
        if (port) {
            url.port = port;
        }
    }
    url.pathname = `${url.pathname.replace(/\/$/, "")}/recrypt_header`;
    return url.toString();
}

/**
 * Re-encrypt a dataset header to the compute keypair with the user-side recryptor service,
 * turning its failures into messages users can act on.
 */
async function recryptHeader(serviceUrl: string, userHeader: string): Promise<RecryptServiceResponse> {
    try {
        const { data } = await axios.post<RecryptServiceResponse>(serviceUrl, { crypt4gh_header: userHeader });
        return data;
    } catch (err) {
        const status = (err as { response?: { status?: number } }).response?.status;
        if (status === undefined) {
            throw new Error(
                `Could not reach the Crypt4GH recryptor service on your machine at ${new URL(serviceUrl).origin}. ` +
                    "Check that it is running and that your browser trusts its certificate.",
                { cause: err },
            );
        }
        if (status === 422) {
            throw new Error("Your Crypt4GH key cannot open this dataset, it was not encrypted for you.", {
                cause: err,
            });
        }
        throw new Error(
            `The Crypt4GH recryptor service on your machine failed (HTTP ${status}). ` +
                "Check that it can reach the compute recryptor service.",
            { cause: err },
        );
    }
}

async function fetchProtectionStatus(datasetId: string): Promise<DatasetProtectionStatus> {
    const { data, error } = await GalaxyApi().GET("/api/datasets/{dataset_id}/protection", {
        params: { path: { dataset_id: datasetId } },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

/**
 * Protection status of a dataset for the current user, and the flow to authorize
 * computation on it.
 *
 * Authorizing sends the dataset's public Crypt4GH header to the recryptor service
 * running on the user's machine, which re-encrypts it to the compute keypair with
 * the user's private key. The result is registered with Galaxy as a grant bound to
 * the current user; it is never stored with the dataset.
 */
export function useDatasetProtection(datasetId: Ref<string>, protectedDataset: Ref<boolean>) {
    const status = ref<DatasetProtectionStatus | null>(null);
    const authorizing = ref(false);

    async function loadStatus() {
        if (!protectedDataset.value) {
            status.value = null;
            return;
        }
        try {
            status.value = await fetchProtectionStatus(datasetId.value);
        } catch (err) {
            status.value = null;
            Toast.error(errorMessageAsString(err, "Failed to load the dataset protection status."));
        }
    }

    async function authorize(userHeader: string | undefined) {
        if (authorizing.value) {
            return;
        }
        if (!userHeader) {
            Toast.error("Dataset does not have a stored Crypt4GH header.", "Authorization failed");
            return;
        }
        authorizing.value = true;
        try {
            const configStore = useConfigStore();
            const userStore = useUserStore();
            const configuredServiceUrl = configStore.config?.crypt4gh_user_service_url;
            if (!configuredServiceUrl) {
                throw new Error("No Crypt4GH recryptor service is configured.");
            }
            const serviceUrl = getRecryptServiceUrl(
                configuredServiceUrl,
                userStore.currentPreferences?.extra_user_preferences,
            );
            const recrypted = await recryptHeader(serviceUrl, userHeader);
            const { data, error } = await GalaxyApi().PUT("/api/datasets/{dataset_id}/protection", {
                params: { path: { dataset_id: datasetId.value } },
                body: {
                    scheme: "crypt4gh",
                    crypt4gh_compute_header: recrypted.crypt4gh_header,
                    crypt4gh_compute_keypair_id: recrypted.crypt4gh_compute_keypair_id,
                    crypt4gh_compute_keypair_expiration_date: recrypted.crypt4gh_compute_keypair_expiration_date,
                },
            });
            if (error) {
                rethrowSimple(error);
            }
            status.value = data;
            Toast.success("This dataset can now be used in your jobs.");
        } catch (err) {
            Toast.error(errorMessageAsString(err, "Crypt4GH authorization failed."), "Authorization failed");
        } finally {
            authorizing.value = false;
        }
    }

    watch([datasetId, protectedDataset], loadStatus, { immediate: true });

    return { status, authorizing, authorize, loadStatus };
}
