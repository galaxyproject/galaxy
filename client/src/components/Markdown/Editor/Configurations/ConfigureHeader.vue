<template>
    <div class="d-flex justify-content-between align-items-start w-100">
        <div class="flex-grow-1 me-3">
            <Heading size="sm" separator>Attach Data</Heading>
            <div class="small mb-2">Fill in the fields below to map required inputs to this cell.</div>
        </div>
        <div class="d-flex gap-1">
            <GButton
                v-if="hasChanged !== undefined"
                transparent
                color="blue"
                icon-only
                tooltip
                tooltip-placement="bottom"
                title="Apply Changes"
                @click="$emit('ok')">
                <FontAwesomeIcon :icon="faCheck" fixed-width />
            </GButton>
            <GButton
                transparent
                color="blue"
                icon-only
                tooltip
                tooltip-placement="bottom"
                title="Cancel"
                @click="onCancel">
                <FontAwesomeIcon :icon="faTimes" fixed-width />
            </GButton>
        </div>
    </div>
</template>

<script setup lang="ts">
import { faCheck, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import { useConfirmDialog } from "@/composables/confirmDialog";

import GButton from "@/components/BaseComponents/GButton.vue";
import Heading from "@/components/Common/Heading.vue";

const props = withDefaults(
    defineProps<{
        hasChanged?: boolean;
    }>(),
    {
        hasChanged: undefined,
    },
);

const emit = defineEmits<{
    (e: "ok"): void;
    (e: "cancel"): void;
}>();

const { confirm } = useConfirmDialog();

async function onCancel() {
    if (props.hasChanged) {
        const confirmed = await confirm(
            "If you proceed without applying these changes, your modifications will be lost. Would you like to apply the changes now, or discard them and keep the previous configuration?",
            {
                title: "You have pending changes",
                okText: "Apply Changes",
                okColor: "red",
                okIcon: faCheck,
                cancelText: "Discard Changes",
            },
        );

        if (confirmed) {
            emit("ok");
        } else if (confirmed === false) {
            emit("cancel");
        }
    } else {
        emit("cancel");
    }
}
</script>
