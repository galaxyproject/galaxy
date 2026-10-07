<script setup lang="ts">
import { faChevronDown, faChevronRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";

import { copy } from "@/utils/clipboard";

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

function sectionDepth(sectionId: string): number {
    return sectionPath(sectionId).length - 1;
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

function copyExample(event: MouseEvent) {
    const target = event.target;
    if (!(target instanceof Element)) {
        return;
    }
    const button = target.closest<HTMLButtonElement>(".authoring-code-example-copy");
    const code = button?.closest(".authoring-code-example")?.querySelector("code")?.textContent;
    if (button && code !== undefined) {
        copy(code, "Example copied to clipboard.");
    }
}

defineExpose({ openSection });

onMounted(() => {
    panel.value?.addEventListener("click", expandLinkedSection);
    panel.value?.addEventListener("click", copyExample);
});
onBeforeUnmount(() => {
    panel.value?.removeEventListener("click", expandLinkedSection);
    panel.value?.removeEventListener("click", copyExample);
});
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
                v-show="isVisible(section.id)"
                :id="section.id"
                :key="section.id"
                class="authoring-help-section"
                :class="{ 'authoring-help-section-nested': section.parentId }"
                :style="{ marginLeft: `${sectionDepth(section.id)}rem` }">
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

.authoring-help-body {
    padding-left: 1.5rem;
    overflow-x: auto;
}

.authoring-help-body :deep(pre),
.authoring-help-intro :deep(pre) {
    overflow-x: auto;
}

.authoring-help-body :deep(.authoring-code-example) {
    margin: 0.75rem 0 1rem;
    overflow: hidden;
    border: 1px solid $border-color;
    border-radius: $border-radius-base;
    background: $body-bg;
}

.authoring-help-body :deep(.authoring-code-example-header) {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.35rem 0.6rem;
    border-bottom: 1px solid $border-color;
    background: $table-heading-bg;
}

.authoring-help-body :deep(.authoring-code-example-label) {
    font-size: 0.75rem;
    font-weight: 600;
}

.authoring-help-body :deep(.authoring-code-example-copy) {
    padding: 0.15rem 0.45rem;
    border: 1px solid $border-color;
    border-radius: $border-radius-base;
    background: $body-bg;
    color: $text-color;
    font-size: 0.75rem;
    cursor: pointer;
}

.authoring-help-body :deep(.authoring-code-example-copy:hover) {
    border-color: $brand-primary;
    color: $brand-primary;
}

.authoring-help-body :deep(.authoring-code-example pre) {
    margin: 0;
    border: 0;
    border-radius: 0;
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

.authoring-help-body :deep(a[href^="#"]:has(code)) {
    color: $brand-primary;
    font-weight: 600;
    text-decoration: none;
}

.authoring-help-body :deep(a[href^="#"] code) {
    color: $code-color;
}

.authoring-help-body :deep(a[href^="#"]:hover code) {
    border-color: $brand-primary;
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
