<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faMagnet, faMousePointer } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useMagicKeys, whenever } from "@vueuse/core";
import { BButton, BButtonGroup, BFormInput } from "bootstrap-vue";
import { computed, toRefs } from "vue";

import { useUid } from "@/composables/utils/uid";
import { useWorkflowStores } from "@/composables/workflowStores";
import { match } from "@/utils/utils";

library.add(faMagnet, faMousePointer);

const { toolbarStore } = useWorkflowStores();
const { snapActive, currentTool } = toRefs(toolbarStore);

const snapButtonTitle = computed(() => {
    if (snapActive.value) {
        return "Deactivate snapping (Ctrl + 2)";
    } else {
        return "Activate snapping (Ctrl + 2)";
    }
});

function onClickPointer() {
    currentTool.value = "pointer";
}

const snappingDistanceId = useUid("snapping-distance-");

const snappingDistanceRangeValue = computed({
    get() {
        return match(toolbarStore.snapDistance, {
            10: () => "1",
            20: () => "2",
            50: () => "3",
            100: () => "4",
            200: () => "5",
        });
    },
    set(value) {
        toolbarStore.snapDistance = match(parseInt(value), {
            1: () => 10,
            2: () => 20,
            3: () => 50,
            4: () => 100,
            5: () => 200,
        });
    },
});

const { ctrl_1, ctrl_2 } = useMagicKeys();

whenever(ctrl_1!, () => (toolbarStore.currentTool = "pointer"));
whenever(ctrl_2!, () => (toolbarStore.snapActive = !toolbarStore.snapActive));
</script>

<template>
    <div class="workflow-editor-toolbar">
        <div class="tools">
            <BButtonGroup vertical>
                <BButton
                    v-b-tooltip.hover.noninteractive.right
                    class="button"
                    title="Pointer Tool (Ctrl + 1)"
                    :pressed="currentTool === 'pointer'"
                    variant="outline-primary"
                    @click="onClickPointer">
                    <FontAwesomeIcon icon="fa-mouse-pointer" size="lg" />
                </BButton>
                <BButton
                    v-b-tooltip.hover.noninteractive.right
                    class="button"
                    :title="snapButtonTitle"
                    :pressed.sync="snapActive"
                    variant="outline-primary">
                    <FontAwesomeIcon icon="fa-magnet" size="lg" />
                </BButton>
            </BButtonGroup>
        </div>
        <div class="options">
            <div
                v-if="
                    toolbarStore.snapActive &&
                    !['freehandAnnotation', 'freehandEraser'].includes(toolbarStore.currentTool)
                "
                class="option wide">
                <label :for="snappingDistanceId" class="flex-label">
                    <span class="font-weight-bold">Snapping Distance</span>
                    {{ toolbarStore.snapDistance }} pixels
                </label>
                <BFormInput
                    :id="snappingDistanceId"
                    v-model="snappingDistanceRangeValue"
                    type="range"
                    min="1"
                    max="5"
                    step="1" />
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.workflow-editor-toolbar {
    position: absolute;
    top: 0;
    left: 0;
    z-index: 2000;
    pointer-events: none;
    display: flex;

    .tools {
        display: flex;
        flex-direction: column;
        padding: 0.25rem;
        gap: 0.25rem;
        pointer-events: auto;

        .button {
            padding: 0;
            display: grid;
            place-items: center;
            height: 2.25rem;
            width: 2.25rem;
        }

        &:deep(.btn-outline-primary) {
            &:not(.active) {
                background-color: $workflow-editor-bg;

                &:hover {
                    background-color: $brand-primary;
                }
            }
        }
    }

    .options {
        display: flex;
        height: 3rem;
        padding: 0.25rem;
        gap: 1rem;
        pointer-events: auto;

        .option {
            display: flex;
            flex-direction: column;
            position: relative;

            &.small {
                width: 6rem;
            }

            &.wide {
                width: 12rem;
            }

            label {
                margin-bottom: 0;
            }

            &:not(:last-child)::after {
                content: "";
                position: absolute;
                top: 0.5rem;
                bottom: 0.5rem;
                width: 0;
                right: calc(-0.5rem - 1px);
                align-self: stretch;
                border: 1px solid $border-color;
            }

            &.buttons {
                flex-direction: row;
                align-items: center;
            }

            .button {
                height: 2rem;
                padding: 0 0.5rem;
            }

            &:deep(.btn-outline-primary) {
                &:not(.active) {
                    background-color: $workflow-editor-bg;
                }

                &:hover {
                    background-color: $brand-primary;
                }
            }
        }
    }
}

.flex-label {
    display: flex;
    justify-content: space-between;
}

.colour-selector {
    position: relative;
}

.icon-t {
    font-size: 1.2rem;
}
</style>
