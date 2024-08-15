<script setup lang="ts">
import { onMounted, ref, watch } from "vue";

import localize from "@/utils/localization";

import ClickToEdit from "@/components/Collections/common/ClickToEdit.vue";

interface Props {
    element: any;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (event: "onRename", name: string): void;
    (event: "element-is-selected", element: any): void;
    (event: "element-is-discarded", element: any): void;
}>();

const elementName = ref("");

watch(elementName, () => {
    emit("onRename", elementName.value);
});

function clickDiscard() {
    emit("element-is-discarded", props.element);
}

onMounted(() => {
    elementName.value = props.element.name;
});
</script>

<template>
    <div class="collection-element" @click="emit('element-is-selected', element)">
        <ClickToEdit v-model="elementName" :title="localize('Click to rename')" />

        <button class="discard-btn btn-sm" :title="localize('Remove this dataset from the list')" @click="clickDiscard">
            {{ localize("Discard") }}
        </button>
    </div>
</template>

<style scoped lang="scss">
.collection-element {
    height: auto;

    .discard-btn {
        float: right;
    }
}
</style>
