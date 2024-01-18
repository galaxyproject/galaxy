<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheck, faPlus, faTags, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import type { Ref } from "vue";
import { computed, nextTick, ref } from "vue";
import Multiselect from "vue-multiselect";

import { useToast } from "@/composables/toast";
import { useUid } from "@/composables/utils/uid";
import { useUserTagsStore } from "@/stores/userTagsStore";

import HeadlessMultiselect from "./HeadlessMultiselect.vue";
import Tag from "./Tag.vue";

interface StatelessTagsProps {
    value?: string[];
    disabled?: boolean;
    clickable?: boolean;
    useToggleLink?: boolean;
    maxVisibleTags?: number;
    placeholder?: string;
}

const props = withDefaults(defineProps<StatelessTagsProps>(), {
    value: () => [],
    disabled: false,
    clickable: false,
    useToggleLink: true,
    maxVisibleTags: 5,
    placeholder: "Add Tags",
});

const emit = defineEmits<{
    (e: "input", tags: string[]): void;
    (e: "tag-click", tag: string): void;
}>();

library.add(faTags, faCheck, faTimes, faPlus);

const userTagsStore = useUserTagsStore();
const { userTags } = storeToRefs(userTagsStore);
const { warning } = useToast();

function onAddTag(tag: string) {
    const newTag = tag.trim();

    if (isValid(newTag)) {
        userTagsStore.addLocalTag(newTag);
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

const multiselectElement: Ref<Multiselect | null> = ref(null);

async function openMultiselect() {
    editing.value = true;
    await nextTick();
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

function isValid(tag: string) {
    return !tag.match(invalidTagRegex);
}

function onTagClicked(tag: string) {
    emit("tag-click", tag);
}
</script>

<template>
    <div class="stateless-tags">
        <div v-if="!disabled" class="tags-edit">
            <div class="interactive-tags">
                <Tag
                    v-for="tag in tags"
                    :key="tag"
                    :option="tag"
                    :editable="true"
                    :clickable="props.clickable"
                    @deleted="onDelete"
                    @click="onTagClicked"></Tag>
            </div>

            <HeadlessMultiselect
                v-if="editing"
                :options="userTags"
                :selected="tags"
                :placeholder="props.placeholder"
                :validator="isValid"
                @close="editing = false"
                @addOption="onAddTag"
                @input="onInput" />
            <button v-else class="toggle-button" @click="openMultiselect">
                {{ props.placeholder }}
                <FontAwesomeIcon icon="fa-tags" />
            </button>
        </div>

        <div v-else>
            <div class="d-inline">
                <Tag
                    v-for="tag in trimmedTags"
                    :key="tag"
                    :option="tag"
                    :editable="false"
                    :clickable="props.clickable"
                    @click="onTagClicked"></Tag>
                <BButton
                    v-if="slicedTags.length > 0 && !toggledOpen"
                    :id="toggleButtonId"
                    variant="link"
                    class="toggle-link"
                    @click="() => (toggledOpen = true)">
                    {{ slicedTags.length }} more...
                </BButton>

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

    .toggle-button {
        font-size: $font-size-base;
        color: $text-color;
        text-decoration: none;
        padding: 0 0.25rem;
        background: none;
        cursor: text;
        text-align: left;
        margin: 0;
        border: none;
        width: 100%;
        height: 1.75rem;
    }

    &:deep(.multiselect) {
        min-height: unset;
        display: flex;
        flex-direction: column-reverse;

        .multiselect__select {
            top: unset;
            bottom: 0;
            padding: 0;
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
            padding: 0;
            background: none;
            font-size: $font-size-base;
            border: none;
            min-height: 0;
        }

        .multiselect__content-wrapper {
            top: 100%;
            z-index: 800;
            width: calc(100% - 4px);
            box-shadow: 0 0 6px 0 rgba(3, 0, 34, 0.048), 0 0 4px 0 rgba(3, 0, 34, 0.185);
        }

        &.multiselect--above .multiselect__content-wrapper {
            top: unset;
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
                background-color: $brand-secondary;

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
