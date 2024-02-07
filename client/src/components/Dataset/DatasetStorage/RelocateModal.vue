<script setup lang="ts">
import { ref } from "vue";

import { ConcreteObjectStoreModel } from "@/api";

import RelocateDialog from "./RelocateDialog.vue";

interface RelocateModalProps {
    fromObjectStore: ConcreteObjectStoreModel;
    targetObjectStores: ConcreteObjectStoreModel[];
}

defineProps<RelocateModalProps>();

const show = ref(false);

function showModal() {
    show.value = true;
}

function hideModal() {
    show.value = false;
}

const emit = defineEmits<{
    (e: "relocate", value: string): void;
}>();

function relocate(objectStoreId: string) {
    emit("relocate", objectStoreId);
}

const title = "Relocate Dataset Storage";

defineExpose({
    showModal,
    hideModal,
});
</script>

<template>
    <b-modal v-model="show" hide-footer>
        <template v-slot:modal-title>
            <h2>{{ title }}</h2>
        </template>
        <RelocateDialog
            :from-object-store="fromObjectStore"
            :target-object-stores="targetObjectStores"
            @relocate="relocate" />
    </b-modal>
</template>
