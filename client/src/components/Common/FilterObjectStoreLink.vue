<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";

import { ConcreteObjectStoreModel } from "@/api";

import ObjectStoreSelect from "./ObjectStoreSelect.vue";
import SelectModal from "@/components/Dataset/DatasetStorage/SelectModal.vue";

library.add(faTimes);

interface FilterObjectStoreLinkProps {
    value: String | null;
    objectStores: ConcreteObjectStoreModel[];
}

const props = defineProps<FilterObjectStoreLinkProps>();

const showModal = ref(false);

const emit = defineEmits<{
    (e: "change", objectStoreId: string | null): void;
}>();

function onSelect(objectStoreId: string | null) {
    emit("change", objectStoreId);
    showModal.value = false;
}

const selectionText = computed(() => {
    if (props.value) {
        return props.value;
    } else {
        return "(any)";
    }
});
</script>

<template>
    <span class="filter-objectstore-link">
        <SelectModal v-model="showModal" title="Select Storage Source">
            <ObjectStoreSelect :object-stores="objectStores" @select="onSelect" />
        </SelectModal>
        <b-link href="#" @click="showModal = true">{{ selectionText }}</b-link>
        <span v-if="value" v-b-tooltip.hover title="Remove Filter">
            <FontAwesomeIcon icon="times" @click="onSelect(null)" />
        </span>
    </span>
</template>
