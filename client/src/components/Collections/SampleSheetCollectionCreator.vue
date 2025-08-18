<script lang="ts" setup>
import type { SampleSheetCollectionType } from "@/api/datasetCollections";
import type { ExtendedCollectionType } from "@/components/Form/Elements/FormData/types";
import { useConfig } from "@/composables/config";

import SampleSheetWizard from "./SampleSheetWizard.vue";

const { config, isConfigLoaded } = useConfig();

interface Props {
    collectionType: SampleSheetCollectionType;
    extendedCollectionType: ExtendedCollectionType;
    extensions?: string[];
}

defineProps<Props>();
</script>

<template>
    <div class="sample-sheet-collection-creator">
        <SampleSheetWizard
            v-if="isConfigLoaded"
            :collection-type="collectionType"
            :extended-collection-type="extendedCollectionType"
            :file-sources-configured="config.file_sources_configured"
            :ftp-upload-site="config.ftp_upload_site" />
    </div>
</template>
