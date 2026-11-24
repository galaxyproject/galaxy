<script setup lang="ts">
import { faEye, faEyeSlash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import type { ToolOutputActions, ToolOutputPreview } from "@/api/tools";
import localize from "@/utils/localization";

import StatelessTags from "../TagsMultiselect/StatelessTags.vue";
import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

const props = defineProps<{
    output: ToolOutputPreview;
    actions?: ToolOutputActions;
}>();

const emit = defineEmits<{
    (e: "update", outputName: string, actions: ToolOutputActions): void;
}>();

const elementId = computed(() => `tool-form-output-${props.output.name}`);
const renameId = computed(() => `${elementId.value}-rename`);
const addTagsId = computed(() => `${elementId.value}-add-tags`);
const removeTagsId = computed(() => `${elementId.value}-remove-tags`);
const hideId = computed(() => `${elementId.value}-hide`);

const title = computed(() => props.output.label || props.output.name);

const details = computed(() => {
    const output = props.output;
    const parts: string[] = [];
    if (output.collection_type) {
        parts.push(output.collection_type);
        if (output.element_count !== null && output.element_count !== undefined) {
            parts.push(`${output.element_count} ${output.element_count === 1 ? "element" : "elements"}`);
        }
    }
    if (output.format) {
        parts.push(output.format);
    } else if (output.output_type === "parameter") {
        parts.push(localize("parameter value"));
    } else {
        parts.push(localize("datatype set when the job runs"));
    }
    if (output.dynamic) {
        parts.push(localize("datasets found when the job runs"));
    }
    return parts.join(" · ");
});

const renameLabel = computed(() => localize(`New name for ${props.output.name}`));

const rename = computed({
    get: () => props.actions?.rename ?? "",
    set: (value: string | null) => update({ rename: value || null }),
});

const addTags = computed(() => props.actions?.add_tags ?? []);

const removeTags = computed(() => props.actions?.remove_tags ?? []);

const hidden = computed(() => props.output.hidden || (props.actions?.hide ?? false));

const hideTitle = computed(() => {
    if (props.output.hidden) {
        return localize("The tool hides this output");
    }
    return hidden.value
        ? localize("Hidden once the job finishes, click to show")
        : localize("Hide once the job finishes");
});

const hideIcon = computed(() => (hidden.value ? faEyeSlash : faEye));

function update(changes: Partial<ToolOutputActions>) {
    const current: ToolOutputActions = {
        rename: props.actions?.rename ?? null,
        add_tags: addTags.value,
        remove_tags: removeTags.value,
        hide: props.actions?.hide ?? false,
    };
    emit("update", props.output.name, { ...current, ...changes });
}

function onToggleHide() {
    update({ hide: !hidden.value });
}

function onAddTags(tags: string[]) {
    update({ add_tags: tags });
}

function onRemoveTags(tags: string[]) {
    update({ remove_tags: tags });
}
</script>

<template>
    <div class="tool-form-output" :data-output-name="props.output.name">
        <div class="d-flex align-items-start">
            <div class="flex-grow-1">
                <span class="font-weight-bold mr-2" data-description="output title">{{ title }}</span>
                <span class="text-muted small" data-description="output details">
                    <span class="text-monospace text-break mr-1">{{ props.output.name }}</span
                    >{{ details }}
                </span>
            </div>
            <GButton
                :id="hideId"
                class="ml-2 px-1"
                size="small"
                transparent
                tooltip
                :title="hideTitle"
                :pressed="hidden"
                :disabled="props.output.hidden"
                data-description="output hide"
                @click="onToggleHide">
                <FontAwesomeIcon :icon="hideIcon" fixed-width />
            </GButton>
        </div>
        <div class="d-flex flex-wrap align-items-center output-controls">
            <GFormInput
                :id="renameId"
                v-model="rename"
                class="output-rename"
                size="small"
                :placeholder="localize('New name (optional)')"
                :aria-label="renameLabel" />
            <div :id="addTagsId" :aria-label="localize('Tags to add')" role="group">
                <StatelessTags
                    inline
                    :model-value="addTags"
                    :placeholder="localize('Add tags')"
                    @update:model-value="onAddTags" />
            </div>
            <div
                :id="removeTagsId"
                v-g-tooltip.hover
                :title="localize('Tags the output would get from its inputs, e.g. name: tags, that it should not keep')"
                :aria-label="localize('Tags to remove')"
                role="group">
                <StatelessTags
                    inline
                    :model-value="removeTags"
                    :placeholder="localize('Remove tags')"
                    @update:model-value="onRemoveTags" />
            </div>
        </div>
    </div>
</template>

<style scoped>
.tool-form-output {
    padding: 0.5rem 0;
}

.tool-form-output + .tool-form-output {
    border-top: 1px solid var(--color-grey-200);
}

.output-controls {
    gap: 0.25rem 0.75rem;
    margin-top: 0.25rem;
}

.output-rename {
    flex: 0 1 22rem;
    min-width: 12rem;
}
</style>
