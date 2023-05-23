<script setup lang="ts">
import { BButton } from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { gxDuotoneMagnet } from "./icons";
import { useWorkflowEditorToolbarStore } from "@/stores/workflowEditorToolbarStore";
import { toRefs } from "vue";

library.add(gxDuotoneMagnet);

const { snapActive } = toRefs(useWorkflowEditorToolbarStore());
</script>

<template>
    <div class="tool-panel">
        <b-button :pressed.sync="snapActive" :variant="snapActive ? 'info' : 'secondary'">
            <FontAwesomeIcon :icon="['gxd', 'magnet']" size="2x" />
        </b-button>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.tool-panel {
    position: absolute;
    top: 0;
    left: 0;
    display: flex;
    flex-direction: column;
    z-index: 1002;
    padding: 0.25rem;
    gap: 0.25rem;

    &:deep(button) {
        padding: 0;
        display: grid;
        place-items: center;
        height: 2.25rem;
        width: 2.25rem;

        &.active {
            --fa-secondary-color: #{$brand-secondary};
        }
    }
}
</style>
