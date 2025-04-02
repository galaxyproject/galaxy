<template>
    <div class="d-flex justify-content-between align-items-start w-100">
        <div class="flex-grow-1 me-3">
            <Heading size="sm" separator>Attach Data</Heading>
            <div class="small mb-2">Fill in the fields below to map required inputs to this cell.</div>
        </div>
        <div class="d-flex gap-1">
            <CellButton
                v-if="hasChanged !== undefined"
                title="Apply Changes"
                tooltip-placement="bottom"
                :icon="faCheck"
                @click="$emit('ok')" />
            <CellButton title="Cancel" tooltip-placement="bottom" :icon="faTimes" @click="onCancel" />
        </div>
        <BModal :visible="showModal">
            <template v-slot:modal-header>
                <Heading size="md">You have pending changes</Heading>
            </template>
            <span v-localize>
                If you proceed without applying these changes, your modifications will be lost. Would you like to apply
                the changes now, or discard them and keep the previous configuration?
            </span>
            <template v-slot:modal-footer>
                <BButton variant="secondary" @click="$emit('cancel')">
                    <FontAwesomeIcon :icon="faTimes" />
                    <span v-localize>Discard Changes</span>
                </BButton>
                <BButton variant="danger" @click="$emit('ok')">
                    <FontAwesomeIcon :icon="faCheck" />
                    <span v-localize>Apply Changes</span>
                </BButton>
            </template>
        </BModal>
    </div>
</template>

<script setup lang="ts">
import { faCheck, faTimes } from "@fortawesome/free-solid-svg-icons";
import { BModal } from "bootstrap-vue";
import { ref } from "vue";

import Heading from "@/components/Common/Heading.vue";
import CellButton from "@/components/Markdown/Editor/CellButton.vue";

const props = withDefaults(
    defineProps<{
        hasChanged?: boolean;
    }>(),
    {
        hasChanged: undefined,
    }
);

const emit = defineEmits<{
    (e: "ok"): void;
    (e: "cancel"): void;
}>();

const showModal = ref(false);

function onCancel() {
    if (props.hasChanged) {
        showModal.value = true;
    } else {
        emit("cancel");
    }
}

defineExpose({ showModal });
</script>
