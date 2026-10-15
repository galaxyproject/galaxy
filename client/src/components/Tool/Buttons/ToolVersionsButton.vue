<script setup lang="ts">
import { faCheck, faCube, faCubes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import GDropdown from "@/components/BaseComponents/GDropdown.vue";
import GDropdownItem from "@/components/BaseComponents/GDropdownItem.vue";

interface Props {
    version: string;
    versions: string[];
}

const props = defineProps<Props>();

const emit = defineEmits(["onChangeVersion"]);

const availableVersions = computed(() => [...props.versions].reverse());
</script>

<template>
    <GDropdown
        no-caret
        right
        variant="link"
        aria-label="Select Versions"
        class="tool-versions"
        toggle-class="px-2 py-1"
        size="sm">
        <template v-slot:button-content>
            <FontAwesomeIcon :icon="faCubes" />
        </template>
        <GDropdownItem
            v-for="v of availableVersions"
            :key="v"
            :active="v === props.version"
            @click="() => emit('onChangeVersion', v)">
            <span v-if="v !== props.version">
                <FontAwesomeIcon :icon="faCube" /> <span v-localize>Switch to</span> {{ v }}
            </span>
            <span v-else> <FontAwesomeIcon :icon="faCheck" /> <span v-localize>Selected</span> {{ v }} </span>
        </GDropdownItem>
    </GDropdown>
</template>

<style scoped>
:deep(.dropdown-toggle) {
    min-width: 24px;
    min-height: 24px;
}
</style>
