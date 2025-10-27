<template>
    <div>
        <LoadingSpan v-if="loading" :message="loadingMessage" />
        <Multiselect
            v-if="items && items.length"
            id="single-item-selector"
            v-model="selectedItem"
            class="single-item-selector"
            name="single-item-selector"
            :allow-empty="false"
            :deselect-label="null"
            :select-label="null"
            :disabled="disabled"
            :label="label"
            :options="items"
            :searchable="true"
            :title="title"
            :track-by="trackBy"
            @select="onSelectItem">
            <template v-slot:option="{ option }">
                <span data-test-id="single-item-selector-option" :data-id="option[trackBy]" :data-label="option[label]">
                    {{ option[label] }}
                </span>
            </template>
        </Multiselect>
    </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import Multiselect from "vue-multiselect";

import LoadingSpan from "@/components/LoadingSpan.vue";

// Using `any` here until we can use generics in Vue3
type Item = any;

interface SingleItemSelectorProps {
    /** Indicates if the available items are still loading. */
    loading?: boolean;
    /** The name of the items. Displayed in the loading message. */
    collectionName?: string;
    /** The items that can be selected. */
    items?: Item[];
    /** Whether the selector is disabled. */
    disabled?: boolean;
    /** The initially selected item. */
    currentItem?: Item;
    /** Tooltip/title for the control. */
    title?: string;
    /** The property of the item to display in the dropdown. */
    label?: string;
    /** The property of the item to use as a unique identifier. */
    trackBy?: string;
}

const props = withDefaults(defineProps<SingleItemSelectorProps>(), {
    disabled: false,
    loading: false,
    title: "",
    collectionName: "items",
    items: () => [],
    currentItem: undefined,
    label: "text",
    trackBy: "id",
});

const emit = defineEmits<{
    (e: "update:selected-item", item: Item | null): void;
}>();

const selectedItem = ref<Item | null>(getInitialSelection());

const loadingMessage = computed(() => `Loading ${props.collectionName}...`);

watch(
    () => [props.items, props.currentItem],
    () => {
        selectedItem.value = getInitialSelection();
    },
);

function getInitialSelection(): Item | null {
    const list = props.items || [];
    if (props.currentItem) {
        return list.find((item) => item[props.trackBy] === props.currentItem![props.trackBy]) || props.currentItem;
    }
    if (list.length) {
        return list[0]!;
    }
    return null;
}

function onSelectItem(item: Item | null) {
    emit("update:selected-item", item);
}
</script>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.single-item-selector :deep(.multiselect__tags) {
    background-color: $white;
}

:deep(.single-item-selector.multiselect--disabled .multiselect__tags),
:deep(.single-item-selector.multiselect--disabled .multiselect__single),
:deep(.single-item-selector.multiselect--disabled .multiselect__select) {
    background: transparent !important;
}

:deep(.single-item-selector.multiselect--disabled .multiselect__select) {
    border-bottom-right-radius: 0.25rem;
    border-top-right-radius: 0.25rem;
}
</style>
