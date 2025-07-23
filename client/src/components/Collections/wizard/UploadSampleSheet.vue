<script setup lang="ts">
import { BCardGroup } from "bootstrap-vue";

import type { SampleSheetCollectionType } from "@/api/datasetCollections";
import type { ExtendedCollectionType } from "@/components/Form/Elements/FormData/types";

import CardDownloadWorkbook from "./CardDownloadWorkbook.vue";
import CardEditWorkbook from "./CardEditWorkbook.vue";
import CardUploadWorkbook from "./CardUploadWorkbook.vue";

async function handleWorkbook(base64Content: string) {
    emit("workbookContents", base64Content);
}

interface Props {
    collectionType: SampleSheetCollectionType;
    extendedCollectionType: ExtendedCollectionType;
}

defineProps<Props>();

const emit = defineEmits(["workbookContents", "download"]);
</script>

<template>
    <div class="generate-workbook">
        <BCardGroup deck>
            <CardDownloadWorkbook @download="emit('download')" />
            <CardEditWorkbook />
            <CardUploadWorkbook @workbookContents="handleWorkbook" />
        </BCardGroup>
    </div>
</template>
