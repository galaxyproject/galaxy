<script setup>
import Multiselect from "vue-multiselect";
import Tag from "./Tag.vue";
import { ref } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

const props = defineProps({
    value: {
        type: Array,
        default: () => [],
    },
    options: {
        type: Array,
        default: () => [],
    },
    disabled: {
        type: Boolean,
        default: false,
    },
});

function onAddTag(tag) {
    console.log(tag);
}

const editing = ref(false);

function onOpen() {
    editing.value = true;
}

function onClose() {
    editing.value = false;
}

const multiselectElement = ref(null);

function openMultiselect() {
    multiselectElement.value.activate();
}
</script>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTags, faCheck, faTimes } from "@fortawesome/free-solid-svg-icons";

library.add(faTags, faCheck, faTimes);
</script>

<template>
    <div class="stateless-tags px-1">
        <Multiselect
            v-if="!disabled"
            placeholder="Add Tags"
            class=""
            ref="multiselectElement"
            :value="props.value"
            :options="props.options"
            :multiple="true"
            :taggable="true"
            @tag="onAddTag"
            @open="onOpen"
            @close="onClose">
            <template v-slot:tag="{ option, search, remove }">
                <Tag :option="option" :search="search" :remove="remove" :editable="true"></Tag>
            </template>
            <template v-slot:noOptions> Type to add new tag </template>
            <template v-slot:caret>
                <b-button v-if="!editing" class="toggle-button" variant="link" tabindex="-1" @click="openMultiselect">
                    Add Tags
                    <FontAwesomeIcon icon="fa-tags"></FontAwesomeIcon>
                </b-button>
            </template>
            <template v-slot:option="{ option }">
                <span>{{ option }} Test</span>
            </template>
        </Multiselect>
        <div v-else class="pl-1 pb-2">
            <div class="d-inline">
                <Tag v-for="tag in props.value" :key="tag" :option="tag" :editable="false"></Tag>
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "scss/theme/blue.scss";

.stateless-tags {
    &:deep(.multiselect) {
        min-height: unset;
        display: flex;
        flex-direction: column-reverse;

        .multiselect__select {
            top: unset;
            bottom: 0;
            padding: 0 0.25rem;
            z-index: 1;
            height: $font-size-base * 2;
        }

        .multiselect__placeholder {
            display: none;
        }

        .multiselect__tags-wrap {
            margin-bottom: 0.5rem;
        }

        .multiselect__tags {
            padding: 0 0.25rem;
            background: none;
            font-size: $font-size-base;
            border: none;
            min-height: 0;
        }

        .multiselect__content-wrapper {
            top: 100%;
            z-index: 800;
        }

        &.multiselect--above .multiselect__content-wrapper {
            top: unset;
        }

        .multiselect__input,
        .toggle-button {
            font-size: $font-size-base;
            color: $text-color;
            text-decoration: none;
            padding: 0;
            background: none;
            cursor: text;
            text-align: left;
            margin: 0;
            border: none;
        }

        .multiselect__input {
            padding-left: 0.25rem;
        }

        .toggle-button {
            padding-left: 0.5rem;
        }
    }
}
</style>
