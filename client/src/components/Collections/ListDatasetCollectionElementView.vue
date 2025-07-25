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
    }
);
</script>

<template>
    <div
        class="d-flex justify-content-between"
        :data-hid="element.hid"
        :class="{ 'collection-element': !textOnly, 'with-actions': hasActions }"
        role="button"
        data-description="list dataset collection element"
        tabindex="0"
        @keyup.enter="emit('element-is-selected', element)"
        @click="emit('element-is-selected', element)">
        <span class="d-flex flex-gapx-1 align-items-center">
            <span v-if="!hideHid && (element.hid ?? true)" data-description="dataset hid">{{ element.hid }}:</span>
            <strong>
                <ClickToEdit v-if="!notEditable" v-model="elementName" :title="localize('Click to rename')" />
                <span v-else>{{ elementName }}</span>
            </strong>
            <i v-if="!hideExtension && element.extension"> ({{ element.extension }}) </i>
        </span>

        <div v-if="hasActions" class="float-right">
            <i v-if="!selected" class="mr-2">
                <FontAwesomeIcon :icon="faCheck" class="text-success" /> Added to collection
            </i>
            <i v-else class="text-secondary">Selected</i>
            <button class="btn-sm" :title="localize('Remove this dataset from the list')" @click="clickDiscard">
                <FontAwesomeIcon :icon="faMinus" fixed-width />
                {{ localize("Remove") }}
            </button>
        </div>
    </div>
</template>

<style scoped lang="scss">
.collection-element {
    height: auto;
}
</style>
