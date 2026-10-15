<script setup lang="ts">
import { faChevronUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    offset: number;
}
const props = defineProps<Props>();
</script>

<template>
    <GButton
        v-g-tooltip.hover
        class="back-to-top"
        :class="{ show: props.offset > 100 }"
        title="Scroll To Top"
        aria-label="Scroll to top"
        :disabled="props.offset <= 100"
        :tabindex="props.offset <= 100 ? -1 : 0"
        color="blue"
        @click="$emit('click')">
        <FontAwesomeIcon :icon="faChevronUp" />
    </GButton>
</template>

<style lang="scss" scoped>
.back-to-top {
    bottom: 0.25rem;
    right: 0.25rem;
    position: absolute;
    opacity: 0;
    transition: opacity 0.4s;
    z-index: 1000;

    &.show {
        opacity: 1;
    }
}
</style>
