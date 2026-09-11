<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    title: string;
    idleIcon: IconDefinition;
    isBusy?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    isBusy: false,
});

const disabled = computed(() => props.isBusy);

const emit = defineEmits(["onClick"]);
</script>

<template>
    <span v-g-tooltip.hover.bottom :title="title">
        <GButton :disabled="disabled" @click="() => emit('onClick')">
            <FontAwesomeIcon v-if="isBusy" :icon="faSpinner" spin />
            <FontAwesomeIcon v-else :icon="idleIcon" />
        </GButton>
    </span>
</template>
