<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faQuestionCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";

import { useHelpModeStore } from "@/stores/helpmode/helpModeStore";
import localize from "@/utils/localization";

library.add(faQuestionCircle);

const tooltip = localize("Enable/Disable Help Mode");
const { draggableActive } = storeToRefs(useHelpModeStore());
function toggleEnabledStatus() {
    draggableActive.value = !draggableActive.value;
}
</script>

<template>
    <div>
        <BButton
            v-b-tooltip.hover.bottom
            class="help-mode-button nav-link"
            :class="{ highlight: draggableActive }"
            :title="tooltip"
            :aria-label="tooltip"
            variant="link"
            @click="toggleEnabledStatus"
            @keydown.enter="toggleEnabledStatus">
            <FontAwesomeIcon :icon="faQuestionCircle" :class="{ highlight: draggableActive }" size="lg" />
        </BButton>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.highlight {
    color: var(--masthead-text-hover);
}
.help-mode-button {
    background-color: inherit;
    border: 0px transparent;
    cursor: pointer;
    color: inherit;
    outline: none;
    &.highlight {
        color: var(--masthead-text-hover);
    }
}
</style>
