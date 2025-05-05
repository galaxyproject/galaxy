<script lang="ts">
/* cannot use a setup block and get params injection in Vue 2.7 I think */

import { library } from "@fortawesome/fontawesome-svg-core";
import { faLink, faUndo, faUnlink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { type ICellRendererParams } from "ag-grid-community";
import { defineComponent } from "vue";

import { usePairingDatasetTargetsStore } from "@/stores/collectionBuilderItemsStore";

type StoreType = ReturnType<typeof usePairingDatasetTargetsStore>;

library.add(faLink, faUndo, faUnlink);

export default defineComponent({
    components: {
        FontAwesomeIcon,
    },
    data() {
        return {
            params: {} as ICellRendererParams,
        };
    },
    computed: {
        isPaired(): boolean {
            return "forward" in (this.params?.value || {});
        },
        isUnpairedTarget(): boolean {
            const value = this.params?.value || {};
            if ("unpaired" in value) {
                const unpaired = value.unpaired;
                return this.pairingTargetsStore().unpairedTarget == unpaired.id;
            } else {
                return false;
            }
        },
        dragging(): boolean {
            return this.pairingTargetsStore().draggedNodeId == this.params.value.unpaired?.id;
        },
        dropOver() {
            return this.pairingTargetsStore().dropTargetId == this.params.value.unpaired?.id;
        },
    },
    methods: {
        pairingTargetsStore(): StoreType {
            const pinia = this.params.context.pinia;
            const pairingTargetsStore = usePairingDatasetTargetsStore(pinia);
            return pairingTargetsStore;
        },
        onSwap() {
            this.params.context.onSwap(this.params.value);
        },
        onUnpairedClick() {
            this.params.context.onUnpairedClick(this.params.value);
        },
        onDragStart() {
            this.pairingTargetsStore().startDrag(this.params.value.unpaired?.id);
        },
        onDragEnd() {
            this.pairingTargetsStore().endDrag();
        },
        onDragEnter() {
            this.pairingTargetsStore().setDropTarget(this.params.value.unpaired?.id);
        },
        onDragLeave() {
            this.pairingTargetsStore().setDropTarget(null);
        },
        onUnpair() {
            this.params.context.onUnpair(this.params.value);
        },
        onDrop() {
            const pairingTargetsStore = this.pairingTargetsStore();
            const draggedNodeId = pairingTargetsStore.draggedNodeId;
            const dropTargetId = this.params.value.unpaired?.id;

            if (draggedNodeId && draggedNodeId !== dropTargetId) {
                this.params.context.onPair(dropTargetId, draggedNodeId, "drag_and_drop");
            }

            pairingTargetsStore.endDrag(); // Clear drag state
        },
    },
});
</script>
<template>
    <div>
        <div v-if="isPaired" class="paired-datasets-cell">
            <FontAwesomeIcon size="2x" icon="fa-undo" class="paired-action-icon" @click="onSwap" />
            <FontAwesomeIcon size="2x" icon="fa-unlink" class="paired-action-icon" @click="onUnpair" />
            <div class="text-container">
                <span><span class="direction">FORWARD</span> {{ params.value.forward.name }}</span>
                <span><span class="direction">REVERSE</span> {{ params.value.reverse.name }}</span>
            </div>
        </div>
        <div v-else class="paired-datasets-cell">
            <div
                class="icon-wrapper"
                :class="{ dragging: dragging, 'drop-target': dropOver }"
                :draggable="true"
                @click="onUnpairedClick"
                @dragstart="onDragStart"
                @dragover.prevent
                @dragenter="onDragEnter"
                @dragleave="onDragLeave"
                @dragend="onDragEnd"
                @drop="onDrop">
                <FontAwesomeIcon
                    size="2x"
                    icon="fa-link"
                    class="paired-action-icon"
                    :class="{ dragging: dragging, 'active-target': isUnpairedTarget, 'fa-beat': isUnpairedTarget }" />
            </div>
            <div class="text-container">
                <div><span class="direction">UNPAIRED</span></div>
                <div>{{ params.value.unpaired.name }}</div>
            </div>
        </div>
    </div>
</template>

<style lang="scss">
@import "theme/blue.scss";

.paired-datasets-cell {
    display: flex;
    align-items: center; /* Vertically center icon and text */
    height: 100%; /* Ensure it spans the full cell height */
    padding: 5px; /* Add padding for spacing */
    box-sizing: border-box;
    font-weight: bold;
}

.paired-datasets-cell .paired-action-icon {
    margin-right: 10px;
}

.paired-datasets-cell .direction {
    font-weight: normal;
    color: gray;
}

.paired-datasets-cell .icon-wrapper {
    display: flex; /* Ensure the wrapper uses flex layout */
    align-items: center; /* Center the icon within the wrapper */
    justify-content: center; /* Center horizontally for safety */
    margin: 0; /* Remove any default margins */
    padding: 0; /* Remove any default padding */
}

.paired-datasets-cell .dragging {
    color: $brand-primary;
}

.paired-datasets-cell .active-target {
    color: $brand-primary;
}

.paired-datasets-cell .drop-target {
    color: $brand-success;
}

.paired-datasets-cell .text-container {
    display: flex;
    flex-direction: column; /* Stack lines vertically */
    justify-content: center; /* Center the text vertically within its area */
    line-height: 1.2; /* Adjust spacing between lines */
    overflow: hidden; /* Prevent overflow if text is too long */
    white-space: nowrap; /* Prevent wrapping if needed */
    text-overflow: ellipsis; /* Add ellipsis for long text */
}
</style>
