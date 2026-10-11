<script setup lang="ts">
import type { ParsedFetchWorkbookForCollectionCollectionType } from "./types";

import CollectionTypeCards from "@/components/Collections/common/CollectionTypeCards.vue";

interface Props {
    value: ParsedFetchWorkbookForCollectionCollectionType;
}

const emit = defineEmits(["onChange"]);

defineProps<Props>();
</script>

<template>
    <CollectionTypeCards
        :value="value"
        :types="['list', 'list:paired', 'list:paired_or_unpaired', 'list:list', 'list:list:paired']"
        context="builder"
        hide-type
        @select="emit('onChange', $event)" />
</template>
