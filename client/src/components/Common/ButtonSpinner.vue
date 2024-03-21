<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlay, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";

library.add(faPlay, faSpinner);

interface Props {
    title: string;
    wait?: boolean;
    tooltip?: string;
    disabled?: boolean;
}

withDefaults(defineProps<Props>(), {
    wait: false,
    tooltip: undefined,
    disabled: false,
});
</script>

<template>
    <BButton
        v-if="wait"
        v-b-tooltip.hover.bottom
        disabled
        variant="info"
        title="Please Wait..."
        class="d-flex flex-nowrap align-items-center text-nowrap">
        <FontAwesomeIcon :icon="faSpinner" class="mr-2" spin />
        {{ title }}
    </BButton>
    <BButton
        v-else
        v-b-tooltip.hover.bottom
        variant="primary"
        class="d-flex flex-nowrap align-items-center text-nowrap"
        :title="tooltip"
        :disabled="disabled"
        @click="$emit('onClick')">
        <FontAwesomeIcon :icon="faPlay" class="mr-2" />
        {{ title }}
    </BButton>
</template>
