<script setup lang="ts">
import { faCaretDown } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdown, BDropdownItemButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";

import { useUserFlagsStore } from "@/stores/userFlagsStore";

interface Props {
    /**
     * Whether the "switch to column select" button is shown
     */
    showManyButton: boolean;
    /**
     * Whether the "switch to simple select" button is shown
     */
    showMultiButton: boolean;
}

defineProps<Props>();

const emit = defineEmits<{
    (e: "use-many", value: boolean): void;
}>();

const { preferredFormSelectElement } = storeToRefs(useUserFlagsStore());
</script>

<template>
    <div class="d-flex">
        <button v-if="showManyButton" class="ui-link ml-1" @click="emit('use-many', true)">
            switch to column select
        </button>
        <button v-else-if="showMultiButton" class="ui-link ml-1" @click="emit('use-many', false)">
            switch to simple select
        </button>

        <BDropdown toggle-class="inline-icon-button d-block px-1" variant="link" no-caret>
            <template v-slot:button-content>
                <FontAwesomeIcon :icon="faCaretDown" />
                <span class="sr-only">select element preferences</span>
            </template>
            <BDropdownItemButton
                :active="preferredFormSelectElement === 'none'"
                @click="preferredFormSelectElement = 'none'">
                No preference
            </BDropdownItemButton>
            <BDropdownItemButton
                :active="preferredFormSelectElement === 'multi'"
                @click="preferredFormSelectElement = 'multi'">
                Default to simple select
            </BDropdownItemButton>
            <BDropdownItemButton
                :active="preferredFormSelectElement === 'many'"
                @click="preferredFormSelectElement = 'many'">
                Default to column select
            </BDropdownItemButton>
        </BDropdown>
    </div>
</template>
