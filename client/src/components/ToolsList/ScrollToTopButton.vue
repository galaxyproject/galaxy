<template>
    <b-button
        v-b-tooltip.noninteractive.hover
        class="back-to-top"
        :class="{ show: offset > 100 }"
        title="Scroll To Top"
        variant="info"
        @click="$emit('click')">
        <FontAwesomeIcon icon="fa-chevron-up" />
    </b-button>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faChevronUp } from "@fortawesome/free-solid-svg-icons";

library.add(faChevronUp);

export default {
    components: { FontAwesomeIcon },
    props: {
        offset: {
            type: Number,
            default: 0,
        },
    },
};
</script>

<style lang="scss" scoped>
.back-to-top {
    bottom: 0.5rem;
    left: 0.5rem;
    position: absolute;
    opacity: 0;
    transition: opacity 0.4s;

    &.show {
        opacity: 1;
    }
}
</style>
