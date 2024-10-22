<script setup lang="ts">
import axios from "axios";
import { ref, watch } from "vue";

import { type BrowsableFilesSourcePlugin } from "@/api/remoteFiles";
import { useFileSources } from "@/composables/fileSources";

import DOILink from "./DOILink.vue";

const { getFileSourceByUri, isLoading: isLoadingFileSources } = useFileSources({ include: ["rdm"] });

interface Props {
    exportRecordUri?: string;
    rdmFileSources?: BrowsableFilesSourcePlugin[];
}

const props = defineProps<Props>();

const doi = ref<string | undefined>(undefined);

// File sources need to be loaded before we can get the DOI
watch(isLoadingFileSources, async (isLoading) => {
    if (!isLoading) {
        doi.value = await getDOIFromExportRecordUri(props.exportRecordUri);
    }
});

/**
 * Gets the DOI from an export record URI.
 * The URI should be in the format: `<scheme>://<source-id>/<record-id>/<file-name>`.
 * @param uri The target URI of the export record to get the DOI from.
 * @returns The DOI or undefined if it could not be retrieved.
 */
async function getDOIFromExportRecordUri(uri?: string) {
    if (!uri) {
        return undefined;
    }

    const fileSource = getFileSourceByUri(uri);
    if (!fileSource) {
        console.debug("No file source found for URI: ", uri);
        return undefined;
    }
    const repositoryUrl = fileSource.url;
    if (!repositoryUrl) {
        console.debug("Invalid repository URL for file source: ", fileSource);
        return undefined;
    }
    const recordId = getRecordIdFromUri(uri);
    if (!recordId) {
        console.debug("No record ID found for URI: ", uri);
        return undefined;
    }
    const recordUrl = `${repositoryUrl}/api/records/${recordId}`;
    return getDOIFromInvenioRecordUrl(recordUrl);
}

/**
 * Extracts the record ID from a URI.
 * The URI should be in the format: `<scheme>://<source-id>/<record-id>/<file-name>`.
 * @param targetUri The URI to extract the record ID from.
 * @returns The record ID or undefined if it could not be extracted.
 */
function getRecordIdFromUri(targetUri?: string): string | undefined {
    if (!targetUri) {
        return undefined;
    }
    return targetUri.split("//")[1]?.split("/")[1];
}

/**
 * Gets the DOI from an Invenio record URL.
 * @param recordUrl The URL of the record to get the DOI from.
 * @returns The DOI or undefined if it could not be retrieved.
 */
async function getDOIFromInvenioRecordUrl(recordUrl?: string): Promise<string | undefined> {
    if (!recordUrl) {
        return undefined;
    }

    try {
        const response = await axios.get(recordUrl);
        if (response.status !== 200) {
            console.debug("Failed to get record from URL: ", recordUrl);
            return undefined;
        }
        const record = response.data;
        if (!record?.doi) {
            console.debug("No DOI found in record: ", record);
            return undefined;
        }
        return record.doi;
    } catch (error) {
        console.warn("Failed to get record from URL: ", recordUrl, error);
        return undefined;
    }
}
</script>

<template>
    <DOILink v-if="doi" :doi="doi" />
</template>
