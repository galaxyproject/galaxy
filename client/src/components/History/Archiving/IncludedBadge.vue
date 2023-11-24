<script setup lang="ts">
import { computed } from "vue";
import { BBadge } from "bootstrap-vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faCheck, faTimes } from "@fortawesome/free-solid-svg-icons";

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
    <b-badge :variant="variant">
        <FontAwesomeIcon v-if="props.included" icon="check" />
        <FontAwesomeIcon v-else icon="times" />
        {{ props.itemName }}
    </b-badge>
</template>
