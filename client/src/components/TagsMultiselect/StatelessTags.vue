<script setup lang="ts">
import { BButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";

import { useToast } from "@/composables/toast";
import { useUid } from "@/composables/utils/uid";
import { useUserTagsStore } from "@/stores/userTagsStore";

import { VALID_TAG_RE } from "../Tags/model";

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

const userTagsStore = useUserTagsStore();
const { userTags } = storeToRefs(userTagsStore);
const { warning } = useToast();

onMounted(() => {
    userTagsStore.onMultipleNewTagsSeen(props.value);
});

function onAddTag(tag: string) {
    const newTag = tag.trim();

    if (isValid(newTag)) {
        userTagsStore.onNewTagSeen(newTag);
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

function isValid(tag: string) {
    return tag.match(VALID_TAG_RE);
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
                :options="userTags"
                :selected="props.value"
                :placeholder="props.placeholder"
                :validator="isValid"
                @addOption="onAddTag"
                @input="onInput"
                @selected="(tag) => userTagsStore.onTagUsed(tag)" />
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
                    @click.stop="() => (toggledOpen = true)">
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
.stateless-tags {
    .toggle-link {
        padding: 0;
        border: none;

        &:hover {
            background-color: transparent;
            border: none;
        }
    }
}
</style>
