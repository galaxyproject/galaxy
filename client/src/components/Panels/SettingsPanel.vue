<script setup lang="ts">
import { ref } from "vue";

import ActivitySettings from "@/components/ActivityBar/ActivitySettings.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";

const query = ref("");

function onQuery(newQuery: string) {
    query.value = newQuery;
}
</script>

<template>
    <ActivityPanel title="Additional Activities">
        <template v-slot:header>
            <DelayedInput :delay="100" placeholder="Search activities" @change="onQuery" />
        </template>
        <ActivitySettings :query="query" />
    </ActivityPanel>
</template>
