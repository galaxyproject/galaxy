<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheck, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import GBadge from "@/component-library/GBadge.vue";

library.add(faCheck, faTimes);

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
        <FontAwesomeIcon v-if="props.included" icon="check" />
        <FontAwesomeIcon v-else icon="times" />
        {{ props.itemName }}
    </GBadge>
</template>
