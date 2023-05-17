<script setup lang="ts">
import { BButton } from "bootstrap-vue";

const emit = defineEmits(["onArchive"]);

function onArchiveHistory() {
    emit("onArchive");
}
</script>

<template>
    <div>
        <p>
            If you want to remove the history from your <i>active</i> histories but keep it around for reference, you
            can move it to the <b>Archived Histories</b> section, by clicking the button below.
        </p>
        <p>
            You can undo this action at any time, and the history will be moved back to your
            <i>active</i> histories.
        </p>

        <b-button class="archive-history-btn mt-3" variant="primary" @click="onArchiveHistory">
            Archive history
        </b-button>
    </div>
</template>
