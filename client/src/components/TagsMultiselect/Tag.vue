<script setup lang="ts">
import { computed } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { keyedColorScheme } from "@/utils/color";

interface TagProps {
    option: string;
    search?: string;
    editable?: boolean;
    clickable?: boolean;
}

const props = defineProps<TagProps>();

const emit = defineEmits<{
    (e: "click", tag: string): void;
    (e: "deleted", tag: string): void;
}>();

//@ts-ignore bad types
library.add(faTimes);

const color = computed(() => keyedColorScheme(props.option));

function onClick() {
    emit("click", props.option);
}

function onDelete() {
    emit("deleted", props.option);
}

const named = computed(() => props.option?.startsWith("#"));
const searched = computed(() => props.option?.toLowerCase() === props.search?.toLowerCase());
</script>

<template>
    <div
        class="tag btn-transparent-background"
        :data-option="props.option"
        :class="{ editable, clickable, searched }"
        :style="`--color-primary: ${color.primary}; --color-darker: ${color.darker}; --color-dimmed: ${color.dimmed}`"
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

    background-color: var(--color-primary);
    transition: background-color 0.1s;

    padding: 0 0.5rem;
    &.editable {
        padding: 0 0.25rem;
    }

    position: relative;

    &:before {
        content: "";
        width: 100%;
        height: 100%;
        top: 0;
        left: 0;
        position: absolute;
        border-color: var(--color-darker);
        border-radius: inherit;
        pointer-events: none;

        border-style: solid;
        border-width: 0 2px 1px 0;
    }

    &.clickable {
        cursor: pointer;

        &:hover {
            background-color: var(--color-dimmed);
        }
    }

    &.searched {
        outline: 2px solid $brand-danger;
    }
}
</style>
