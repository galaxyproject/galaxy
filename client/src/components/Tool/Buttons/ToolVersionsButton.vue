<script setup>
import { computed } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

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

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheck, faCubes, faCube } from "@fortawesome/free-solid-svg-icons";

library.add(faCheck, faCubes, faCube);
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
            <FontAwesomeIcon icon="fas fa-cubes" />
        </template>
        <b-dropdown-item
            v-for="v of availableVersions"
            :key="v"
            :active="v === props.version"
            @click="() => emit('onChangeVersion', v)">
            <span v-if="v !== props.version">
                <FontAwesomeIcon icon="fas fa-cube" /> <span v-localize>Switch to</span> {{ v }}
            </span>
            <span v-else> <FontAwesomeIcon icon="fas fa-check" /> <span v-localize>Selected</span> {{ v }} </span>
        </b-dropdown-item>
    </b-dropdown>
</template>
