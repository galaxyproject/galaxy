<script setup lang="ts">
import { ref, watch } from "vue";

import type { ParsedFetchWorkbookForCollectionCollectionType } from "./types";

import WhichWorkbookCollectionType from "./WhichWorkbookCollectionType.vue";
import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";

interface Props {
    collectionType: ParsedFetchWorkbookForCollectionCollectionType;
    includeCollectionName: boolean;
}

const props = defineProps<Props>();

const currentCollectionType = ref<ParsedFetchWorkbookForCollectionCollectionType>(props.collectionType);
const currentIncludeCollectionName = ref<boolean>(props.includeCollectionName);

const emit = defineEmits(["onCollectionType", "onIncludeCollectionName"]);

function setCollectionType(type: ParsedFetchWorkbookForCollectionCollectionType) {
    currentCollectionType.value = type;
    emit("onCollectionType", currentCollectionType.value);
}

watch(currentIncludeCollectionName, (newValue) => {
    emit("onIncludeCollectionName", newValue);
});
</script>

<template>
    <div class="configure-workbook">
        <div class="which-question">What type of collection do you want to create?</div>
        <WhichWorkbookCollectionType :value="collectionType" @onChange="setCollectionType" />
        <GCheckbox v-model="currentIncludeCollectionName" class="multiple-collections" size="large">
            Include a collection name column so multiple collections can be created using the workbook?
        </GCheckbox>
    </div>
</template>

<style scoped lang="scss">
.which-question {
    font-size: 1.2rem;
}

.multiple-collections {
    margin-top: 1rem;
    font-size: 1.2rem;
}
</style>
