<script setup lang="ts">
import type { UploadMethodConfig } from "../types";

import ZipImportWizard from "@/components/ImportData/zip/ZipImportWizard.vue";

interface Props {
    method: UploadMethodConfig;
    targetHistoryId: string;
}

defineProps<Props>();
</script>

<template>
    <ZipImportWizard
        :should-display-heading="false"
        :target-history-id="targetHistoryId"
        :show-target-history-warning="false" />
</template>
