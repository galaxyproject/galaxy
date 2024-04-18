<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BTab, BTabs } from "bootstrap-vue";
import { storeToRefs } from "pinia";

import { useMarkdown } from "@/composables/markdown";
import { DEFAULT_HELP_TEXT, useHelpModeStore } from "@/stores/helpmode/helpModeStore";
import localize from "@/utils/localization";

import LoadingSpan from "@/components/LoadingSpan.vue";

const { renderMarkdown } = useMarkdown({
    openLinksInNewPage: true,
    html: true,
    appendHrRuleToDetails: true,
    replaceCodeWithIcon: true,
});

// local refs
const { activeTab, contents, loading, currentTabs } = storeToRefs(useHelpModeStore());

const noHelpTextMsg = localize("No help text available for this component");
</script>

<template>
    <span v-if="!activeTab" v-localize class="help-mode-container">{{ DEFAULT_HELP_TEXT }}</span>
    <BTabs v-else class="help-mode-container">
        <BTab v-for="helpId of currentTabs" :key="helpId" :active="activeTab === helpId">
            <template v-slot:title>
                <FontAwesomeIcon v-if="contents[helpId]?.icon" :icon="contents[helpId]?.icon" />
                {{ contents[helpId]?.title }}
            </template>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div v-if="!loading" v-html="renderMarkdown(contents[helpId]?.content || noHelpTextMsg)" />
            <BAlert v-else variant="info" show>
                <LoadingSpan message="Loading help text" />
            </BAlert>
        </BTab>
    </BTabs>
</template>

<style scoped lang="scss">
.help-mode-container {
    margin-top: 0;
    padding: 10px;
    overflow-y: auto;
    height: 100%;
}
</style>
