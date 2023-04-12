<script setup lang="ts">
import { computed } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faChevronUp, faChevronDown } from "@fortawesome/free-solid-svg-icons";

const props = defineProps({
    description: {
        type: String,
        required: true,
    },
    showDetails: {
        type: Boolean,
        default: false,
    },
    maxLength: {
        type: Number,
        default: 150,
    },
});

const emit = defineEmits<{
    (e: "update:show-details", showDetails: boolean): void;
}>();

const propShowDetails = computed({
    get: () => {
        return props.showDetails;
    },
    set: (val) => {
        emit("update:show-details", val);
    },
});

//@ts-ignore bad library types
library.add(faChevronUp, faChevronDown);
const collapsedEnableIcon = "fas fa-chevron-down";
const collapsedDisableIcon = "fas fa-chevron-up";

// summarized length
const x = Math.round(props.maxLength - props.maxLength / 2);

const summary = computed(() => props.description.length > props.maxLength);
const text = computed(() =>
    props.description.length > props.maxLength ? props.description.slice(0, x) : props.description
);
</script>

<template>
    <div>
        {{ text }}
        <span v-if="summary">
            <a
                v-if="!propShowDetails"
                class="text-summary-expand"
                href="javascript:void(0)"
                @click.stop="propShowDetails = true">
                ... <FontAwesomeIcon :icon="collapsedEnableIcon" />
            </a>
            <a v-else href="javascript:void(0)" @click.stop="propShowDetails = false">
                ... <FontAwesomeIcon :icon="collapsedDisableIcon" />
            </a>
        </span>
    </div>
</template>
