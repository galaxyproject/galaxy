<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown, faCopy, faEye, faPause, faTimesCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BLink } from "bootstrap-vue";
import { computed } from "vue";

import { type HDASummary } from "@/api";

library.add(faCaretDown, faCopy, faEye, faTimesCircle, faPause);

interface Props {
    item: HDASummary;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "copyDataset", item: Props["item"]): void;
    (e: "showDataset", item: Props["item"]): void;
}>();

const getName = computed(() => {
    return props.item.name || "Unavailable";
});
const isError = computed(() => {
    return props.item.state === "error";
});
const isPaused = computed(() => {
    return props.item.state === "paused";
});

function copyDataset() {
    emit("copyDataset", props.item);
}
</script>

<template>
    <div>
        <BLink
            id="dataset-dropdown"
            class="workflow-dropdown p-2"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="false">
            <FontAwesomeIcon
                v-if="isError"
                v-b-tooltip.hover
                :icon="faTimesCircle"
                class="dataset-icon error text-danger"
                title="An error occurred for this dataset." />
            <FontAwesomeIcon
                v-else-if="isPaused"
                v-b-tooltip.hover
                :icon="faPause"
                class="dataset-icon pause text-info"
                title="The creation of this dataset has been paused." />
            <FontAwesomeIcon v-else :icon="faCaretDown" class="dataset-icon" />

            <span class="name">{{ getName }}</span>
        </BLink>

        <div class="dropdown-menu" aria-labelledby="dataset-dropdown">
            <a class="dropdown-item" href="#" @click.prevent="copyDataset">
                <FontAwesomeIcon :icon="faCopy" class="mr-1" />

                <span>Copy to current History</span>
            </a>
        </div>
    </div>
</template>

<style scoped>
.dataset-icon {
    position: relative;
    margin-left: -1rem;
}
</style>
