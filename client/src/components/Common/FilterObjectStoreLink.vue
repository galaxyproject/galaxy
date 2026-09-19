<script setup lang="ts">
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";

import type { UserConcreteObjectStoreModel } from "@/api";
import { useObjectStoreStore } from "@/stores/objectStoreStore";

import GModal from "../BaseComponents/GModal.vue";
import ObjectStoreSelect from "./ObjectStoreSelect.vue";

interface FilterObjectStoreLinkProps {
    value?: string;
    objectStores: UserConcreteObjectStoreModel[];
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
        return "(any)";
    }
});
</script>

<template>
    <span class="filter-objectstore-link">
        <GModal size="small" :show.sync="showModal" title="Select a storage source to filter by">
            <ObjectStoreSelect :object-stores="objectStores" @select="onSelect" />
        </GModal>
        <b-link href="#" @click="showModal = true">{{ selectionText }}</b-link>
        <span v-if="value" v-g-tooltip.hover title="Remove Filter">
            <FontAwesomeIcon :icon="faTimes" @click="onSelect(undefined)" />
        </span>
    </span>
</template>
