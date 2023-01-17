<script setup lang="ts">
import { ref, computed } from "vue";
import Multiselect from "vue-multiselect";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTags, faCheck, faTimes, faPlus } from "@fortawesome/free-solid-svg-icons";
import Tag from "./Tag.vue";
import { useUserTags } from "@/composables/user";
import { useToast } from "@/composables/toast";
import { useUid } from "@/composables/utils/uid";

import type { Ref } from "vue";

interface StatelessTagsProps {
    value?: string[];
    disabled?: boolean;
    clickable?: boolean;
    useToggleLink?: boolean;
    maxVisibleTags?: number;
}

const props = withDefaults(defineProps<StatelessTagsProps>(), {
    value: () => [],
    disabled: false,
    clickable: false,
    useToggleLink: true,
    maxVisibleTags: 5,
});

const emit = defineEmits<{
    (e: "input", tags: string[]): void;
    (e: "tag-click", tag: string): void;
}>();

//@ts-ignore bad library types
library.add(faTags, faCheck, faTimes, faPlus);

const { userTags, addLocalTag } = useUserTags();
const { warning } = useToast();

function onAddTag(tag: string) {
    const newTag = tag.trim();

    if (isValid(newTag)) {
        addLocalTag(newTag);
        emit("input", [...props.value, newTag]);
    } else {
        warning(`"${newTag}" is not a valid tag.`, "Invalid Tag");
    }
}

function onInput(val: string[]) {
    emit("input", val);
}

function onDelete(tag: string) {
    const val = [...tags.value];
    const index = tags.value.indexOf(tag);
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

const multiselectElement: Ref<Multiselect | null> = ref(null);

function openMultiselect() {
    //@ts-ignore bad library types
    multiselectElement.value?.activate();
}

const tags = computed(() => props.value.map((tag) => tag.replace(/^name:/, "#")));

const toggledOpen = ref(false);
const toggleButtonId = useUid("toggle-link-");

const trimmedTags = computed(() => {
    if (!props.useToggleLink || toggledOpen.value) {
        return tags.value;
    } else {
        return tags.value.slice(0, props.maxVisibleTags);
    }
});

const slicedTags = computed(() => {
    if (!props.useToggleLink) {
        return [];
    } else {
        return tags.value.slice(props.maxVisibleTags);
    }
});

const invalidTagRegex = /([.:\s][.:\s])|(^[.:])|([.:]$)|(^[\s]*$)/;

function isValid(tag: string | { label: string }) {
    if (typeof tag === "string") {
        return !tag.match(invalidTagRegex);
    } else {
        return !tag.label.match(invalidTagRegex);
    }
}

function onTagClicked(tag: string) {
    emit("tag-click", tag);
}
</script>

<template>
    <div class="stateless-tags px-1">
        <Multiselect
            v-if="!disabled"
            ref="multiselectElement"
            placeholder="Add Tags"
            open-direction="bottom"
            :value="tags"
            :options="userTags"
            :multiple="true"
            :taggable="true"
            :close-on-select="false"
            @tag="onAddTag"
            @input="onInput"
            @open="onOpen"
            @close="onClose">
            <template v-slot:tag="{ option, search }">
                <Tag
                    :option="option"
                    :search="search"
                    :editable="true"
                    :clickable="props.clickable"
                    @deleted="onDelete"
                    @click="onTagClicked"></Tag>
            </template>

            <template v-slot:noOptions>
                <span class="multiselect-option">Type to add new tag</span>
            </template>

            <template v-slot:caret>
                <b-button v-if="!editing" class="toggle-button" variant="link" tabindex="-1" @click="openMultiselect">
                    Add Tags
                    <FontAwesomeIcon icon="fa-tags" />
                </b-button>
            </template>

            <template v-slot:option="{ option }">
                <span class="multiselect-option" :class="{ invalid: !isValid(option) }">
                    <span>{{ option.label ?? option }}</span>
                    <span v-if="tags.includes(option)" class="float-right">
                        <span class="info">
                            <FontAwesomeIcon class="check-icon" icon="fa-check" fixed-width />
                        </span>

                        <span class="info highlighted">
                            <FontAwesomeIcon class="times-icon" icon="fa-times" fixed-width />
                            <span class="sr-only">remove tag</span>
                        </span>
                    </span>
                    <span v-else class="float-right">
                        <span class="info highlighted">
                            <FontAwesomeIcon class="plus-icon" icon="fa-plus" fixed-width />
                            <span class="sr-only">add tag</span>
                        </span>
                    </span>
                </span>
            </template>
        </Multiselect>

        <div v-else class="pl-1 pb-2">
            <div class="d-inline">
                <Tag
                    v-for="tag in trimmedTags"
                    :key="tag"
                    :option="tag"
                    :editable="false"
                    :clickable="props.clickable"
                    @click="onTagClicked"></Tag>
                <b-button
                    v-if="slicedTags.length > 0 && !toggledOpen"
                    :id="toggleButtonId"
                    variant="link"
                    class="toggle-link"
                    @click="() => (toggledOpen = true)">
                    {{ slicedTags.length }} more...
                </b-button>

                <b-tooltip
                    v-if="slicedTags.length > 0 && !toggledOpen"
                    :target="toggleButtonId"
                    custom-class="stateless-tags--tag-preview-tooltip"
                    placement="bottom">
                    <Tag
                        v-for="tag in slicedTags"
                        :key="tag"
                        :option="tag"
                        :editable="false"
                        :clickable="props.clickable"
                        @click="onTagClicked"></Tag>
                </b-tooltip>
            </div>
        </div>
    </div>
</template>

<style lang="scss">
.stateless-tags--tag-preview-tooltip {
    opacity: 1 !important;
}
</style>

<style lang="scss" scoped>
@import "scss/theme/blue.scss";

.stateless-tags {
    .toggle-link {
        padding: 0;
        border: none;

        &:hover {
            background-color: transparent;
            border: none;
        }
    }

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

            &::before {
                border-color: $text-color transparent transparent;
            }
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
            width: calc(100% - 4px);
            left: 2px;

            box-shadow: 0 0 6px 0 rgba(3, 0, 34, 0.048), 0 0 4px 0 rgba(3, 0, 34, 0.185);
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

        // built in option class
        .multiselect__option {
            min-height: unset;
            padding: 0;

            &::after {
                display: none;
            }

            // custom option wrapper
            .multiselect-option {
                font-size: $font-size-base;
                padding: 0.5rem;
                display: inline-block;
                width: 100%;
                height: 100%;

                .info {
                    display: none;
                }

                &.invalid {
                    color: $brand-light;
                    background-color: $brand-warning;
                }
            }
        }

        .multiselect__option--selected {
            .multiselect-option {
                color: $brand-primary;

                .info:not(.highlighted) {
                    display: inline-block;
                }
            }
        }

        .multiselect__option--highlight {
            &::after {
                display: none;
            }

            .multiselect-option {
                background: $brand-primary;
                color: $brand-light;

                .info.highlighted {
                    display: inline-block;
                }

                .info:not(.highlighted) {
                    display: none;
                }
            }
        }
    }
}
</style>
