<script setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheck, faCube, faCubes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

library.add(faCheck, faCubes, faCube);
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
        title="版本"
        variant="link"
        aria-label="选择版本"
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
                <FontAwesomeIcon icon="fas fa-cube" /> <span v-localize>切换至</span> {{ v }}
            </span>
            <span v-else> <FontAwesomeIcon icon="fas fa-check" /> <span v-localize>已选择</span> {{ v }} </span>
        </b-dropdown-item>
    </b-dropdown>
</template>
