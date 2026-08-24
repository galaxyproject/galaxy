<script setup lang="ts">
import { faChevronDown, faChevronRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import { authoringHelpGroups, authoringHelpIntro, authoringHelpTitle } from "./authoringHelp";
import { highlightAuthoringCode } from "./authoringHelpHighlight";

import GButton from "@/components/BaseComponents/GButton.vue";
import Heading from "@/components/Common/Heading.vue";
import ToolHelpMarkdown from "@/components/Tool/ToolHelpMarkdown.vue";

const expanded = ref<string[]>([]);

function isExpanded(id: string): boolean {
    return expanded.value.includes(id);
}

function toggle(id: string) {
    if (isExpanded(id)) {
        expanded.value = expanded.value.filter((openId) => openId !== id);
    } else {
        expanded.value = [...expanded.value, id];
    }
}
</script>

<template>
    <div class="authoring-help-panel">
        <Heading h2 inline size="sm" class="mb-2">{{ authoringHelpTitle }}</Heading>

        <ToolHelpMarkdown
            class="authoring-help-intro"
            :content="authoringHelpIntro"
            :syntax-highlighter="highlightAuthoringCode" />

        <section v-for="group in authoringHelpGroups" :key="group.id" class="authoring-help-group">
            <Heading h3 size="xs" class="authoring-help-group-title">{{ group.title }}</Heading>

            <div v-for="section in group.sections" :key="section.id" class="authoring-help-section">
                <GButton
                    transparent
                    size="small"
                    class="authoring-help-toggle"
                    :aria-expanded="isExpanded(section.id) ? 'true' : 'false'"
                    :data-description="`toggle help section ${section.id}`"
                    @click="toggle(section.id)">
                    <FontAwesomeIcon :icon="isExpanded(section.id) ? faChevronDown : faChevronRight" fixed-width />
                    {{ section.title }}
                </GButton>
                <ToolHelpMarkdown
                    v-if="isExpanded(section.id)"
                    class="authoring-help-body"
                    :content="section.body"
                    :syntax-highlighter="highlightAuthoringCode" />
            </div>
        </section>
    </div>
</template>

<style scoped>
.authoring-help-panel {
    margin: 0 auto;
    max-width: 60rem;
}

.authoring-help-toggle {
    display: flex;
    width: 100%;
    text-align: left;
    padding-left: 0;
}

.authoring-help-group {
    margin-top: 1rem;
}

.authoring-help-group-title {
    margin-bottom: 0.25rem;
}

.authoring-help-body {
    padding-left: 1.5rem;
}

.authoring-help-body :deep(pre),
.authoring-help-intro :deep(pre) {
    overflow-x: auto;
}

.authoring-help-body :deep(table) {
    display: block;
    overflow-x: auto;
}
</style>
