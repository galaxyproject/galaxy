<script setup>
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

const availableVersions = computed(() => props.versions?.filter((v) => v !== props.version).reverse());
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
            <span class="fa fa-cubes" />
        </template>
        <b-dropdown-item v-for="v of availableVersions" :key="v" @click="emit('onChangeVersion', v)">
            <span class="fa fa-cube" /> <span v-localize>Switch to</span> {{ v }}
        </b-dropdown-item>
    </b-dropdown>
</template>
