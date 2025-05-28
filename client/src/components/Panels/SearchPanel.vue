<script setup lang="ts">
import { computed, ref } from "vue";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";

const currentQuery = ref("");

const searchEmpty = computed(() => currentQuery.value.trim() === "");
</script>

<template>
    <ActivityPanel title="Search">
        <DelayedInput placeholder="search workflow" :delay="200" @change="(v) => (currentQuery = v)" />

        <div v-if="searchEmpty" class="search-help">
            <p>Type to search all steps and comments in the workflow graph.</p>
            <p>Use any of the following keywords to narrow your search:</p>
            <ul>
                <li>step</li>
                <li>input</li>
                <li>output</li>
                <li>comment</li>
            </ul>
        </div>
    </ActivityPanel>
</template>

<style lang="scss" scoped>
.search-help {
    margin-top: var(--spacing-3);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-2);

    p,
    ul {
        margin: 0;
        padding: 0;
    }

    ul {
        padding-left: var(--spacing-4);
    }
}
</style>
