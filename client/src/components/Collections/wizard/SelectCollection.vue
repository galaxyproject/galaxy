<script setup lang="ts">
import { BAlert, BCard, BCardTitle } from "bootstrap-vue";
import { onMounted, ref, watch } from "vue";

import type { ExtendedCollectionType } from "@/components/Form/Elements/FormData/types";
import type { SelectionItem } from "@/components/SelectionDialog/selectionTypes";
import { datasetCollectionDialog } from "@/utils/dataModals";

const emit = defineEmits(["onChange", "onError"]);
const errorMessage = ref<string | undefined>(undefined);
const targetCollection = ref<string | undefined>(undefined);

interface Props {
    collectionType: string;
    extendedCollectionType: ExtendedCollectionType;
}

const props = defineProps<Props>();

function getCompatibleSourceTypes(sampleSheetType: string): string[] | undefined {
    if (sampleSheetType === "sample_sheet") {
        return ["list", "sample_sheet"];
    }
    if (sampleSheetType === "sample_sheet:paired") {
        return ["list:paired", "sample_sheet:paired"];
    }
    if (sampleSheetType === "sample_sheet:paired_or_unpaired") {
        return [
            "list",
            "list:paired",
            "list:paired_or_unpaired",
            "sample_sheet",
            "sample_sheet:paired",
            "sample_sheet:paired_or_unpaired",
        ];
    }
    if (sampleSheetType === "sample_sheet:record") {
        return ["list:record", "sample_sheet:record"];
    }
    return undefined;
}

function inputDialog() {
    const compatibleTypes = getCompatibleSourceTypes(props.collectionType);
    datasetCollectionDialog(
        (data: SelectionItem) => {
            targetCollection.value = data.id;
        },
        {
            collectionTypes: compatibleTypes,
        },
    );
}

watch(targetCollection, () => {
    emit("onChange", targetCollection.value);
});

onMounted(() => {
    inputDialog();
});
</script>

<template>
    <BCard
        class="wizard-selection-card"
        data-description="selection collection card"
        border-variant="primary"
        @click="inputDialog">
        <BCardTitle>
            <b>Select collection</b>
        </BCardTitle>
        <div>
            <BAlert v-if="errorMessage" show variant="danger">{{ errorMessage }}</BAlert>
            Select a dataset collection, the contents will be loaded as tabular data and made available for supplying
            sample sheet metadata.
        </div>
    </BCard>
</template>
