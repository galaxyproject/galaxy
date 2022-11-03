<script setup>
import Multiselect from "vue-multiselect";
import Tag from "./Tag.vue";
import { ref } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useUserTags } from "composables/user";

const props = defineProps({
    value: {
        type: Array,
        default: () => [],
    },
    disabled: {
        type: Boolean,
        default: false,
    },
});

const emit = defineEmits(["input"]);

const { userTags, addLocalTag } = useUserTags();

function onAddTag(tag) {
    addLocalTag(tag);
    emit("input", [...props.value, tag]);
}

function onInput(val) {
    console.log(val);
    emit("input", val);
}

function onDelete(tag) {
    const val = [...props.value];
    const index = props.value.indexOf(tag);
    val.splice(index, 1);
    emit("input", val);
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
import { faTags, faCheck, faTimes, faPlus } from "@fortawesome/free-solid-svg-icons";

library.add(faTags, faCheck, faTimes, faPlus);
</script>

<template>
    <div class="stateless-tags px-1">
        <Multiselect
            v-if="!disabled"
            placeholder="Add Tags"
            class=""
            ref="multiselectElement"
            :value="props.value"
            :options="userTags"
            :multiple="true"
            :taggable="true"
            @tag="onAddTag"
            @input="onInput"
            @open="onOpen"
            @close="onClose">
            <template v-slot:tag="{ option, search }">
                <Tag :option="option" :search="search" :editable="true" @deleted="onDelete"></Tag>
            </template>

            <template v-slot:noOptions> Type to add new tag </template>

            <template v-slot:caret>
                <b-button v-if="!editing" class="toggle-button" variant="link" tabindex="-1" @click="openMultiselect">
                    Add Tags
                    <FontAwesomeIcon icon="fa-tags"></FontAwesomeIcon>
                </b-button>
            </template>

            <template v-slot:option="{ option }">
                <span>{{ option.label ?? option }}</span>
                <span v-if="value.includes(option)" class="float-right">
                    <FontAwesomeIcon class="check-icon" icon="fa-check"></FontAwesomeIcon>
                    <FontAwesomeIcon class="times-icon" icon="fa-times"></FontAwesomeIcon>
                </span>
                <span v-else class="float-right">
                    <FontAwesomeIcon class="plus-icon" icon="fa-plus"></FontAwesomeIcon>
                </span>
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

        .multiselect__option {
            font-size: $font-size-base;
            min-height: unset;
            padding: 0.5rem 1rem;

            .plus-icon {
                display: none;
            }

            &::after {
                display: none;
            }

            &.multiselect__option--selected {
                color: $brand-primary;

                .times-icon {
                    display: none;
                }
            }

            &.multiselect__option--highlight {
                background: $brand-primary;
                color: $brand-light;

                .times-icon,
                .plus-icon {
                    display: inline-block;
                }

                .check-icon {
                    display: none;
                }

                &::after {
                    display: none;
                }
            }
        }
    }
}
</style>
