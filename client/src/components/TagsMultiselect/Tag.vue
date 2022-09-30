<script setup>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { keyedColorScheme } from "utils/color";
import { computed } from "vue";

const props = defineProps({
    option: String,
    search: String,
    remove: Function,
    editable: Boolean,
    focusable: Boolean,
});

const emit = defineEmits(["click"]);

const color = computed(() => keyedColorScheme(props.option).primary);

function onClick() {
    emit("click", props.option);
}
</script>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimes } from "@fortawesome/free-solid-svg-icons";

library.add(faTimes);
</script>

<template>
    <div class="tag" :class="{ editable }" :style="`background-color: ${color};`" @click.prevent.stop="onClick">
        <span>
            {{ props.option }}
        </span>
        <b-button v-if="editable" size="sm" variant="link" class="px-1 py-0" tabindex="-1" @click="props.remove">
            <FontAwesomeIcon icon="fa-times"></FontAwesomeIcon>
        </b-button>
    </div>
</template>

<style lang="scss" scoped>
@import "scss/theme/blue.scss";

.tag {
    display: inline-flex;
    align-items: baseline;

    margin-right: 0.25rem;
    margin-bottom: 0.1rem;

    font-size: $font-size-base * 0.95;
    color: black;
    border-radius: 4px;
    cursor: pointer;

    padding: 0 0.5rem;
    &.editable {
        padding: 0 0.25rem;
    }
}
</style>
