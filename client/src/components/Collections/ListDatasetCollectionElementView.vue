<script setup lang="ts">
import { faCheck, faMinus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref, watch } from "vue";

import localize from "@/utils/localization";

import ClickToEdit from "@/components/Collections/common/ClickToEdit.vue";

interface Props {
    element: any;
    selected?: boolean;
    hasActions?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (event: "onRename", name: string): void;
    (event: "element-is-selected", element: any): void;
    (event: "element-is-discarded", element: any): void;
}>();

const elementName = ref(props.element.name);

watch(elementName, () => {
    emit("onRename", elementName.value);
});

function clickDiscard() {
    emit("element-is-discarded", props.element);
}
</script>

<template>
    <div
        class="collection-element d-flex justify-content-between"
        :class="{ 'with-actions': hasActions }"
        role="button"
        tabindex="0"
        @keyup.enter="emit('element-is-selected', element)"
        @click="emit('element-is-selected', element)">
        <span class="d-flex flex-gapx-1">
            {{ element.hid }}:
            <strong>
                <ClickToEdit v-model="elementName" style="cursor: text" :title="localize('Click to rename')" />
            </strong>
            <i> ({{ element.extension }}) </i>
        </span>

        <div v-if="hasActions" class="float-right">
            <i v-if="!selected" class="mr-2"><FontAwesomeIcon :icon="faCheck" class="text-success" /> Added to list</i>
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
