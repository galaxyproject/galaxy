<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";

import { type ConcreteObjectStoreModel } from "@/api";
import { useObjectStoreStore } from "@/stores/objectStoreStore";

import ObjectStoreSelect from "./ObjectStoreSelect.vue";
import SelectModal from "@/components/Dataset/DatasetStorage/SelectModal.vue";

library.add(faTimes);

interface FilterObjectStoreLinkProps {
    value?: string;
    objectStores: ConcreteObjectStoreModel[];
}

const props = defineProps<FilterObjectStoreLinkProps>();

const { getObjectStoreNameById } = useObjectStoreStore();

const showModal = ref(false);

const emit = defineEmits<{
    (e: "change", objectStoreId?: string): void;
}>();

function onSelect(objectStoreId?: string | null) {
    if (objectStoreId == null) {
        emit("change", undefined);
    } else {
        emit("change", objectStoreId);
    }
    showModal.value = false;
}

const selectionText = computed(() => {
    if (props.value) {
        return getObjectStoreNameById(props.value);
    } else {
        return "(任何)";
    }
});
</script>

<template>
    <span class="filter-objectstore-link">
        <SelectModal v-model="showModal" title="选择存储源">
            <ObjectStoreSelect :object-stores="objectStores" @select="onSelect" />
        </SelectModal>
        <b-link href="#" @click="showModal = true">{{ selectionText }}</b-link>
        <span v-if="value" v-b-tooltip.hover title="移除过滤器">
            <FontAwesomeIcon icon="times" @click="onSelect(undefined)" />
        </span>
    </span>
</template>