<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPen, faSave, faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BFormInput, BFormTextarea } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { useUserStore } from "@/stores/userStore";
import l from "@/utils/localization";

import type { DetailsLayoutSummarized } from "./types";

import ClickToEdit from "@/components/Collections/common/ClickToEdit.vue";
import TextSummary from "@/components/Common/TextSummary.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

library.add(faPen, faSave, faUndo);

interface Props {
    name?: string;
    tags?: string[];
    writeable?: boolean;
    annotation?: string;
    showAnnotation?: boolean;
    summarized?: DetailsLayoutSummarized;
}

const props = withDefaults(defineProps<Props>(), {
    name: undefined,
    tags: undefined,
    writeable: true,
    annotation: undefined,
    showAnnotation: true,
    summarized: undefined,
});

const emit = defineEmits(["save"]);

const userStore = useUserStore();
const { isAnonymous } = storeToRefs(userStore);

const nameRef = ref<HTMLInputElement | null>(null);

const editing = ref(false);
const textSelected = ref(false);
const localProps = ref<{ name: string; annotation: string | null; tags: string[] }>({
    name: "",
    annotation: "",
    tags: [],
});

const clickToEditName = computed({
    get: () => props.name,
    set: (newName) => {
        if (newName && newName !== props.name) {
            emit("save", { name: newName.trim() });
            localProps.value.name = newName;
        }
    },
});

const detailsClass = computed(() => {
    const classes: Record<string, boolean> = {
        details: true,
        "summarized-details": !!props.summarized,
        "m-3": !props.summarized || editing.value,
    };

    if (props.summarized) {
        classes[props.summarized] = true;
    }

    return classes;
});

const editButtonTitle = computed(() => {
    if (isAnonymous.value) {
        return l("Log in to Rename History");
    } else {
        if (props.writeable) {
            return l("Edit");
        } else {
            return l("Not Editable");
        }
    }
});

function onSave() {
    editing.value = false;
    emit("save", localProps.value);
}

function onToggle() {
    editing.value = !editing.value;

    localProps.value = {
        name: props.name,
        annotation: props.annotation,
        tags: props.tags,
    };

    if (nameRef.value) {
        nameRef.value.focus();
    }
}

function selectText() {
    if (!textSelected.value) {
        nameRef.value?.select();
        textSelected.value = true;
    } else {
        nameRef.value?.focus();
        textSelected.value = false;
    }
}
</script>

<template>
    <section :class="detailsClass" data-description="edit details">
        <div class="d-flex justify-content-between w-100">
            <ClickToEdit
                v-if="!summarized"
                v-model="clickToEditName"
                component="h3"
                title="..."
                data-description="name display"
                no-save-on-blur
                class="my-2 w-100" />
            <div v-else style="max-width: 80%">
                <TextSummary
                    :description="name"
                    data-description="name display"
                    class="my-2"
                    component="h3"
                    one-line-summary
                    no-expand />
            </div>

            <BButton
                :disabled="isAnonymous || !writeable"
                class="edit-button ml-1 float-right"
                data-description="editor toggle"
                size="sm"
                variant="link"
                :title="editButtonTitle"
                :pressed="editing"
                @click="onToggle">
                <FontAwesomeIcon :icon="faPen" fixed-width />
            </BButton>
        </div>

        <slot name="description" />

        <div v-if="!editing">
            <div
                v-if="annotation && !summarized"
                v-short="annotation"
                class="mt-2"
                data-description="annotation value" />
            <div
                v-else-if="summarized"
                :class="{ annotation: ['both', 'annotation'].includes(summarized), hidden: summarized === 'hidden' }">
                <TextSummary
                    v-if="annotation"
                    :description="annotation"
                    data-description="annotation value"
                    one-line-summary
                    no-expand />
            </div>
            <StatelessTags
                v-if="tags"
                :class="{
                    'mt-2': !summarized,
                    tags: ['both', 'tags'].includes(summarized),
                    hidden: summarized === 'hidden',
                }"
                :value="tags"
                disabled
                :max-visible-tags="summarized ? 1 : 5" />
            <slot v-if="summarized" name="update-time" />
        </div>

        <div v-else class="mt-3" data-description="edit form">
            <BFormInput
                v-if="summarized"
                ref="name"
                v-model="localProps.name"
                class="mb-2"
                placeholder="Name"
                trim
                max-rows="4"
                data-description="name input"
                @keyup.enter="onSave"
                @keyup.esc="onToggle"
                @focus="selectText"
                @blur="textSelected = false" />

            <BFormTextarea
                v-if="showAnnotation"
                v-model="localProps.annotation"
                class="mb-2"
                placeholder="Annotation (optional)"
                trim
                max-rows="4"
                data-description="annotation input"
                @keyup.esc="onToggle" />

            <StatelessTags v-if="localProps.tags" v-model="localProps.tags" class="mb-3 tags" />

            <BButton
                class="save-button mb-1"
                data-description="editor save button"
                size="sm"
                variant="primary"
                :disabled="!localProps.name"
                @click="onSave">
                <FontAwesomeIcon :icon="faSave" fixed-width />
                <span v-localize>Save</span>
            </BButton>

            <BButton
                class="cancel-button mb-1"
                data-description="editor cancel button"
                size="sm"
                icon="undo"
                @click="onToggle">
                <FontAwesomeIcon :icon="faUndo" fixed-width />
                <span v-localize>Cancel</span>
            </BButton>
        </div>
    </section>
</template>

<style lang="scss" scoped>
.summarized-details {
    margin-left: 0.5rem;
    max-width: 15rem;

    &.both {
        min-height: 8.5em;
    }
    .tags {
        min-height: 2rem;
    }
    .annotation {
        min-height: 2rem;
    }
    .hidden {
        display: none;
    }
}
</style>
