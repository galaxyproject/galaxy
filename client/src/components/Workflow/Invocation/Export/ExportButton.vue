<script setup lang="ts">
import { type IconDefinition, library } from "@fortawesome/fontawesome-svg-core";
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed } from "vue";

library.add(faSpinner);

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
    <span v-b-tooltip.hover.bottom :title="title">
        <BButton :disabled="disabled" @click="() => emit('onClick')">
            <FontAwesomeIcon v-if="isBusy" :icon="faSpinner" spin />
            <FontAwesomeIcon v-else :icon="idleIcon" />
        </BButton>
    </span>
</template>
