<script setup lang="ts">
import { faCheck, faCube, faCubes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import GButton from "@/components/BaseComponents/GButton.vue";
import GDropdown from "@/components/BaseComponents/GDropdown.vue";
import GDropdownItem from "@/components/BaseComponents/GDropdownItem.vue";

interface Props {
    version: string;
    versions: string[];
}

const props = withDefaults(defineProps<Props>(), {
    versions: () => [],
});

const emit = defineEmits(["onChangeVersion"]);

const availableVersions = computed(() => [...props.versions].reverse());
</script>

<template>
    <GDropdown
        no-caret
        right
        role="button"
        variant="link"
        aria-label="Select Versions"
        class="tool-versions"
        toggle-class="p-0"
        size="sm">
        <template v-slot:button-content>
            <GButton class="d-block" color="blue" transparent size="small" tooltip title="Versions">
                <FontAwesomeIcon :icon="faCubes" />
            </GButton>
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
