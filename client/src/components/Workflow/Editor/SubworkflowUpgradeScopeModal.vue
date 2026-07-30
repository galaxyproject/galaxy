<script setup lang="ts">
import { computed } from "vue";

import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

const props = defineProps<{
    show: boolean;
    /**
     * Workflows that exist in the user's own list and would get a new version if the upgrade is
     * applied to them rather than to a private copy.
     */
    sharedWorkflowNames: string[];
}>();

const emit = defineEmits<{
    (e: "update:show", show: boolean): void;
    /** detach true keeps the upgrade inside this workflow, false updates the shared workflows too. */
    (e: "confirm", detach: boolean): void;
}>();

const workflowList = computed(() => props.sharedWorkflowNames.join(", "));
const plural = computed(() => props.sharedWorkflowNames.length > 1);

function choose(detach: boolean) {
    // confirm first: closing is also what a dismissal looks like, and the caller treats a
    // dismissal as "do nothing", so it has to see the answer before it sees the close.
    emit("confirm", detach);
    emit("update:show", false);
}
</script>

<template>
    <GModal
        :show="show"
        title="Where should this upgrade apply?"
        size="medium"
        footer
        @update:show="emit('update:show', $event)">
        <p>
            This subworkflow {{ plural ? "uses workflows that are" : "is a workflow that is" }} also in your workflow
            list: <b>{{ workflowList }}</b
            >.
        </p>
        <p>
            Upgrading {{ plural ? "them" : "it" }} here gives {{ plural ? "them" : "it" }} a new version, which every
            other workflow using {{ plural ? "them" : "it" }} will see the next time it is upgraded. Keeping the change
            here instead copies {{ plural ? "them" : "it" }} into this workflow, so nothing else is affected, but this
            workflow stops following {{ plural ? "their" : "its" }} future versions.
        </p>

        <template v-slot:footer>
            <GButton @click="choose(true)">Only in this workflow</GButton>
            <GButton color="blue" @click="choose(false)">
                Also update {{ plural ? "those workflows" : "that workflow" }}
            </GButton>
            <GButton transparent @click="emit('update:show', false)">Cancel</GButton>
        </template>
    </GModal>
</template>
