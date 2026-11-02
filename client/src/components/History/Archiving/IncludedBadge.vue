<script setup lang="ts">
import { faCheck, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import GBadge from "@/components/BaseComponents/GBadge.vue";

interface Props {
    itemName: string;
    included: boolean;
}

const props = defineProps<Props>();

const variant = computed(() => {
    return props.included ? "primary" : "secondary";
});
</script>

<template>
    <GBadge :variant="variant">
        <FontAwesomeIcon v-if="props.included" :icon="faCheck" />
        <FontAwesomeIcon v-else :icon="faTimes" />
        {{ props.itemName }}
    </GBadge>
</template>
