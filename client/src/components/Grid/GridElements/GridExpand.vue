<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faChevronDown, faChevronUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BLink } from "bootstrap-vue";

library.add(faChevronDown, faChevronUp);

interface Props {
    detailsShowing?: boolean;
}
const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "show-details", show: boolean): void;
}>();

function showDetails() {
    if (props.detailsShowing === undefined) {
        emit("show-details", true);
    } else {
        emit("show-details", !props.detailsShowing);
    }
}
</script>

<template>
    <BLink data-description="toggle row details" @click.stop="showDetails">
        <FontAwesomeIcon
            :title="props.detailsShowing ? 'Hide details' : 'Show details'"
            size="lg"
            :icon="props.detailsShowing ? faChevronUp : faChevronDown" />
    </BLink>
</template>
