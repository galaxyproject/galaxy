<script setup lang="ts">
import axios from "axios";
import { ref, watch } from "vue";

import { BrowsableFilesSourcePlugin } from "@/api/remoteFiles";
import { useFileSources } from "@/composables/fileSources";

import DOILink from "./DOILink.vue";

// TODO: This should be using a store so we don't have to load file sources in every component
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

async function getDOIFromExportRecordUri(targetUri?: string) {
    if (!targetUri) {
        return undefined;
    }

    const fileSource = getFileSourceByUri(targetUri);
    if (!fileSource) {
        console.debug("No file source found for URI: ", targetUri);
        return undefined;
    }
    if (!fileSource.url) {
        console.debug("Invalid file source for URI: ", targetUri);
        return undefined;
    }
    const recordId = getRecordIdFromUri(targetUri);
    if (!recordId) {
        console.debug("No record ID found for URI: ", targetUri);
        return undefined;
    }
    const recordUrl = `${fileSource.url}/api/records/${recordId}`;
    return getDOIFromRecordUrl(recordUrl);
}

function getRecordIdFromUri(targetUri?: string): string | undefined {
    if (!targetUri) {
        return undefined;
    }
    return targetUri.split("//")[1]?.split("/")[1];
}

async function getDOIFromRecordUrl(recordUrl?: string): Promise<string | undefined> {
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
