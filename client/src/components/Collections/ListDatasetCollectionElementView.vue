<script setup lang="ts">
import { faCheck, faMinus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref, watch } from "vue";

import type { HDASummary } from "@/api";
import localize from "@/utils/localization";

import ClickToEdit from "@/components/Collections/common/ClickToEdit.vue";

interface Props {
    element: HDASummary;
    selected?: boolean;
    hasActions?: boolean;
    notEditable?: boolean;
    hideExtension?: boolean;
    hideHid?: boolean;
    textOnly?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (event: "onRename", name: string): void;
    (event: "element-is-selected", element: any): void;
    (event: "element-is-discarded", element: any): void;
}>();

const elementName = ref(props.element.name || "...");

watch(elementName, () => {
    emit("onRename", elementName.value);
});

function clickDiscard() {
    emit("element-is-discarded", props.element);
}

watch(
    () => props.element.name,
    () => {
        elementName.value = props.element.name || "...";
    },
);
</script>

<template>
    <component
        :is="notEditable && !hasActions ? 'button' : 'div'"
        :type="notEditable && !hasActions ? 'button' : undefined"
        :aria-pressed="notEditable && !hasActions ? (selected ? 'true' : 'false') : undefined"
        class="d-flex justify-content-between"
        :data-hid="element.hid"
        :class="{ 'collection-element': !textOnly, 'with-actions': hasActions }"
        data-description="list dataset collection element"
        @click="emit('element-is-selected', element)">
        <button
            v-if="hasActions"
            type="button"
            class="dataset-selection-button"
            :aria-label="`${localize('Select dataset')} ${elementName}`"
            :aria-pressed="selected ? 'true' : 'false'"
            @click.stop="emit('element-is-selected', element)">
            <FontAwesomeIcon :icon="faCheck" :class="{ 'text-muted': !selected }" />
        </button>
        <span class="d-flex flex-gapx-1 align-items-center flex-grow-1">
            <span v-if="!hideHid && (element.hid ?? true)" data-description="dataset hid">{{ element.hid }}:</span>
            <strong>
                <ClickToEdit
                    v-if="!notEditable"
                    :value="elementName"
                    :title="localize('Click to rename')"
                    @input="(v: string) => (elementName = v)" />
                <span v-else>{{ elementName }}</span>
            </strong>
            <i v-if="!hideExtension && element.extension"> ({{ element.extension }}) </i>
        </span>

        <div v-if="hasActions" class="float-right">
            <i v-if="!selected" class="mr-2">
                <FontAwesomeIcon :icon="faCheck" class="dataset-added-icon" /> Added to collection
            </i>
            <i v-else class="text-secondary">Selected</i>
            <button
                type="button"
                class="btn-sm"
                :title="localize('Remove this dataset from the list')"
                @click.stop="clickDiscard">
                <FontAwesomeIcon :icon="faMinus" fixed-width />
                {{ localize("Remove") }}
            </button>
        </div>
    </component>
</template>

<style scoped lang="scss">
.dataset-selection-button {
    border: 0;
    background: transparent;
    color: inherit;
    min-width: 24px;
    min-height: 24px;
    padding: 0;
    margin-right: 4px;
}

.dataset-added-icon {
    color: #237c3b;
}

.collection-element {
    height: auto;
    min-height: 24px;
    text-align: left;
    color: inherit;
    background: transparent;
}
</style>
