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
            The "Apply Rules" tool allows you to transform an existing collection using the same set of rules as can be
            used to import new data.
        </div>
    </BCard>
</template>
