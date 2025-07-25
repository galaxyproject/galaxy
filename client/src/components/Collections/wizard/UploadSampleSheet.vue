<script setup lang="ts">
import { BCardGroup } from "bootstrap-vue";
import { computed } from "vue";

import type { SampleSheetCollectionType } from "@/api/datasetCollections";
import { getDownloadWorkbookUrl } from "@/components/Collections/sheet/workbooks";
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

const props = defineProps<Props>();

const emit = defineEmits(["workbookContents"]);

const generateWorkbookHref = computed(() => {
    return getDownloadWorkbookUrl(props.extendedCollectionType.columnDefinitions!, props.collectionType);
});
</script>

<template>
    <div class="generate-workbook">
        <BCardGroup deck>
            <CardDownloadWorkbook :generate-workbook-link="generateWorkbookHref" />
            <CardEditWorkbook />
            <CardUploadWorkbook @workbookContents="handleWorkbook" />
        </BCardGroup>
    </div>
</template>
