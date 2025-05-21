<script setup>
import { faCheck, faCube, faCubes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

const props = defineProps({
    version: {
        type: String,
        required: true,
    },
    versions: {
        type: Array,
        default: null,
    },
});

const emit = defineEmits(["onChangeVersion"]);

const availableVersions = computed(() => [...props.versions].reverse());
</script>

<template>
    <b-dropdown
        v-b-tooltip.hover
        no-caret
        right
        role="button"
        title="Versions"
        variant="link"
        aria-label="Select Versions"
        class="tool-versions"
        size="sm">
        <template v-slot:button-content>
            <FontAwesomeIcon :icon="faCubes" />
        </template>
        <b-dropdown-item
            v-for="v of availableVersions"
            :key="v"
            :active="v === props.version"
            @click="() => emit('onChangeVersion', v)">
            <span v-if="v !== props.version">
                <FontAwesomeIcon :icon="faCube" /> <span v-localize>Switch to</span> {{ v }}
            </span>
            <span v-else> <FontAwesomeIcon :icon="faCheck" /> <span v-localize>Selected</span> {{ v }} </span>
        </b-dropdown-item>
    </b-dropdown>
</template>
