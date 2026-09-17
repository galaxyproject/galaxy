<script setup lang="ts">
import localize from "@/utils/localization";

import GButton from "@/components/BaseComponents/GButton.vue";

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
        <GButton tabindex="-1" @click="emit('clicked-cancel')">
            {{ localize("Cancel") }}
        </GButton>

        <GButton class="create-collection" color="blue" :disabled="!validInput" @click="emit('clicked-create')">
            {{ localize("Create " + shortWhatIsBeingCreated) }}
        </GButton>
    </div>
</template>
