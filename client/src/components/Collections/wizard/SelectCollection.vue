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

function inputDialog() {
    const collectionType = props.collectionType;
    datasetCollectionDialog(
        (data: SelectionItem) => {
            targetCollection.value = data.id;
        },
        {
            // TODO: use this in that dialog.
            collectionType: collectionType,
        }
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
