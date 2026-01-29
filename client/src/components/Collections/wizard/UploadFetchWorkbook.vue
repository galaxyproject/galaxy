<script setup lang="ts">
import { BCardGroup } from "bootstrap-vue";
import { computed } from "vue";

import { withPrefix } from "@/utils/redirect";

import type { ParsedFetchWorkbookForCollectionCollectionType, RulesCreatingWhat } from "./types";

import CardDownloadWorkbook from "./CardDownloadWorkbook.vue";
import CardEditWorkbook from "./CardEditWorkbook.vue";
import CardUploadWorkbook from "./CardUploadWorkbook.vue";

async function handleWorkbook(base64Content: string) {
    emit("workbookContents", base64Content);
}

interface Props {
    creatingWhat: RulesCreatingWhat;
    collectionType: ParsedFetchWorkbookForCollectionCollectionType;
    includeCollectionName: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits(["workbookContents"]);

const generateWorkbookHref = computed(() => {
    let type;
    if (props.creatingWhat === "datasets") {
        type = "datasets";
    } else if (props.includeCollectionName) {
        type = "collections";
    } else {
        type = "collection";
    }
    // const type = props.creatingWhat === "collections" ? "collection" : "dataset";
    let url = `/api/tools/fetch/workbook?type=${type}`;
    if (type === "collection" || type === "collections") {
        url = `${url}&collection_type=${props.collectionType}`;
    }
    return withPrefix(url);
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
