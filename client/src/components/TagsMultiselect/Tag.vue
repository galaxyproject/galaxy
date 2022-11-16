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
    clickable: Boolean,
});

const emit = defineEmits(["click", "deleted"]);

const color = computed(() => keyedColorScheme(props.option));

function onClick() {
    emit("click", props.option);
}

function onDelete() {
    emit("deleted", props.option);
}

const named = computed(() => props.option.startsWith("#"));
</script>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimes } from "@fortawesome/free-solid-svg-icons";

library.add(faTimes);
</script>

<template>
    <div
        class="tag btn-transparent-background"
        :data-option="props.option"
        :class="{ editable, clickable }"
        :style="`background-color: ${color.primary}; border-color: ${color.darker}`"
        @click.prevent.stop="onClick">
        <span :class="{ 'font-weight-bold': named }">
            {{ props.option }}
        </span>
        <b-button
            v-if="editable"
            size="sm"
            variant="link"
            class="px-1 py-0 tag-delete-button"
            tabindex="-1"
            @click.prevent.stop="onDelete">
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

    padding: 0 0.5rem;
    &.editable {
        padding: 0 0.25rem;
    }

    &.clickable {
        cursor: pointer;
        position: relative;

        &:hover {
            &:before {
                content: "";
                width: 100%;
                height: 100%;
                top: 0;
                left: 0;
                position: absolute;
                border: 2px solid;
                border-color: inherit;
                border-radius: inherit;
                pointer-events: none;
            }
        }
    }
}
</style>
