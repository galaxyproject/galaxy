<script setup lang="ts">
import localize from "@/utils/localization";

interface Props {
    validInput: boolean;
    shortWhatIsBeingCreated: string;
}

defineProps<Props>();

const emit = defineEmits<{
    (e: "clicked-create"): void;
    (e: "clicked-cancel"): void;
}>();
</script>

<template>
    <div class="actions vertically-spaced d-flex justify-content-between">
        <BButton tabindex="-1" @click="emit('clicked-cancel')">
            {{ localize("Cancel") }}
        </BButton>

        <BButton class="create-collection" variant="primary" :disabled="!validInput" @click="emit('clicked-create')">
            {{ localize("Create " + shortWhatIsBeingCreated) }}
        </BButton>
    </div>
</template>
