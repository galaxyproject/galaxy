<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faChevronUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";

library.add(faChevronUp);

interface Props {
    offset: number;
}
const props = withDefaults(defineProps<Props>(), {
    offset: 0,
});
</script>

<template>
    <BButton
        v-b-tooltip.noninteractive.hover
        class="back-to-top"
        :class="{ show: props.offset > 100 }"
        :title="props.offset > 100 ? '回到顶部' : ''"
        variant="info"
        @click="$emit('click')">
        <FontAwesomeIcon icon="fa-chevron-up" />
    </BButton>
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
