<script setup lang="ts">
import { BCard, BCardTitle } from "bootstrap-vue";

import { borderVariant } from "@/components/Common/Wizard/utils";

interface Props {
    selected: boolean;
}

defineProps<Props>();

const emit = defineEmits(["select"]);
</script>

<template>
    <BCard
        data-import-source-from="collection"
        class="wizard-selection-card"
        :border-variant="borderVariant(selected)"
        @click="emit('select', 'collection')">
        <BCardTitle>
            <b>An Existing Collection</b>
        </BCardTitle>
        <div>
            <!-- TODO: replace collection with an english expression -->
            Fill in sample sheet data from an existing collection.
        </div>
    </BCard>
</template>
