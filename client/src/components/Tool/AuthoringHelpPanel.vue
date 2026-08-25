<script setup lang="ts">
import { faChevronDown, faChevronRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";

import { authoringHelpGroups, authoringHelpIntro, authoringHelpTitle } from "./authoringHelp";
import { highlightAuthoringCode } from "./authoringHelpHighlight";

import GButton from "@/components/BaseComponents/GButton.vue";
import Heading from "@/components/Common/Heading.vue";
import ToolHelpMarkdown from "@/components/Tool/ToolHelpMarkdown.vue";

const expanded = ref<string[]>([]);
const panel = ref<HTMLElement>();
const sections = authoringHelpGroups.flatMap((group) => group.sections);
const sectionsById = new Map(sections.map((section) => [section.id, section]));

function isExpanded(id: string): boolean {
    return expanded.value.includes(id);
}

function isVisible(id: string): boolean {
    const parentId = sectionsById.get(id)?.parentId;
    return !parentId || (isExpanded(parentId) && isVisible(parentId));
}

function sectionPath(sectionId: string): string[] {
    const path: string[] = [];
    let currentId: string | undefined = sectionId;
    while (currentId) {
        path.unshift(currentId);
        currentId = sectionsById.get(currentId)?.parentId;
    }
    return path;
}

function toggle(id: string) {
    if (isExpanded(id)) {
        expanded.value = expanded.value.filter((openId) => openId !== id);
    } else {
        expanded.value = [...expanded.value, id];
    }
}

async function openSection(sectionId: string): Promise<boolean> {
    if (!sectionsById.has(sectionId)) {
        return false;
    }
    expanded.value = [...new Set([...expanded.value, ...sectionPath(sectionId)])];
    await nextTick();
    const linkedSection = Array.from(panel.value?.querySelectorAll<HTMLElement>(".authoring-help-section") ?? []).find(
        (element) => element.id === sectionId,
    );
    linkedSection?.scrollIntoView?.({ block: "start" });
    return true;
}

async function expandLinkedSection(event: MouseEvent) {
    const target = event.target;
    if (!(target instanceof Element)) {
        return;
    }
    const link = target.closest<HTMLAnchorElement>('a[href^="#"]');
    const sectionId = link?.hash.slice(1);
    const hasSection = authoringHelpGroups.some((group) => group.sections.some((section) => section.id === sectionId));
    if (sectionId && hasSection) {
        event.preventDefault();
        await openSection(sectionId);
    }
}

defineExpose({ openSection });

onMounted(() => panel.value?.addEventListener("click", expandLinkedSection));
onBeforeUnmount(() => panel.value?.removeEventListener("click", expandLinkedSection));
</script>

<template>
    <div ref="panel" class="authoring-help-panel">
        <Heading h2 inline size="sm" class="mb-2">{{ authoringHelpTitle }}</Heading>

        <ToolHelpMarkdown
            class="authoring-help-intro"
            :content="authoringHelpIntro"
            :syntax-highlighter="highlightAuthoringCode" />

        <section v-for="group in authoringHelpGroups" :key="group.id" class="authoring-help-group">
            <Heading h3 size="xs" class="authoring-help-group-title">{{ group.title }}</Heading>

            <div
                v-for="section in group.sections"
                :id="section.id"
                :key="section.id"
                v-show="isVisible(section.id)"
                class="authoring-help-section"
                :class="{ 'authoring-help-section-nested': section.parentId }">
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

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

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

.authoring-help-section-nested {
    margin-left: 1rem;
}

.authoring-help-body {
    padding-left: 1.5rem;
    overflow-x: auto;
}

.authoring-help-body :deep(pre),
.authoring-help-intro :deep(pre) {
    overflow-x: auto;
}

.authoring-help-body :deep(table) {
    width: 100%;
    margin: 0.75rem 0 1rem;
    border: 1px solid $border-color;
    border-collapse: collapse;
}

.authoring-help-body :deep(th),
.authoring-help-body :deep(td) {
    padding: 0.6rem 0.75rem;
    border: 1px solid $border-color;
    text-align: left;
    vertical-align: top;
}

.authoring-help-body :deep(th) {
    background: $table-heading-bg;
    font-weight: 600;
}

.authoring-help-body :deep(tbody tr:nth-child(odd)) {
    background: $table-bg-accent;
}

.authoring-help-body :deep(td code) {
    display: inline-block;
    padding: 0.1rem 0.3rem;
    border: 1px solid $border-color;
    background: $body-bg;
    color: $code-color;
    white-space: nowrap;
}

.authoring-help-body :deep(td a) {
    color: $brand-primary;
    font-weight: 600;
    text-decoration: underline;
    text-underline-offset: 0.15em;
}

.authoring-help-body :deep(td a code) {
    color: inherit;
    border-color: currentColor;
}

.authoring-help-body :deep(td a:hover code) {
    background: rgba($brand-primary, 0.08);
}

.authoring-help-body :deep(th:first-child) {
    width: 10rem;
}

.authoring-help-body :deep(th:nth-last-child(-n + 2)) {
    width: 6rem;
    white-space: nowrap;
}
</style>
