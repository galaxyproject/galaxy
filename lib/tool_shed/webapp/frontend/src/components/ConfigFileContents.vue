<script setup lang="ts">
import { GButton } from "@galaxyproject/galaxy-ui"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faCopy, faDownload } from "@fortawesome/free-solid-svg-icons"
import { copyAndNotify, downloadTextFile, notify } from "@/util"

interface ConfigFileContentsProps {
    name: string
    contents: string
    what: string
}

async function copyContents() {
    copyAndNotify(props.contents, `${props.what} copied to your clipboard`)
}

function downloadContents() {
    try {
        downloadTextFile(props.name, props.contents)
    } catch (e) {
        notify("Your browser does not allow this operation")
    }
}

const props = defineProps<ConfigFileContentsProps>()
</script>
<template>
    <section class="config-file-contents">
        <div class="config-file-contents-heading">
            <span class="config-file-contents-name">{{ name }}</span>
            <GButton icon-only transparent size="small" aria-label="Copy contents" title="Copy" @click="copyContents">
                <FontAwesomeIcon :icon="faCopy" />
            </GButton>
            <GButton
                icon-only
                transparent
                size="small"
                aria-label="Download"
                title="Download"
                @click="downloadContents"
            >
                <FontAwesomeIcon :icon="faDownload" />
            </GButton>
        </div>
        <pre class="config-file-contents-body">{{ contents }}</pre>
    </section>
</template>

<style scoped>
/* A dark code block, as config snippets are on the other Galaxy sites */
.config-file-contents {
    margin: 0.75rem 0;
    overflow: hidden;
    background: var(--color-ebony-clay-950, #212532);
    border-radius: var(--shed-radius-sm);
}

.config-file-contents-heading {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.3rem 0.4rem 0.3rem 0.9rem;
    background: var(--color-ebony-clay-900, #2c3143);
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.config-file-contents-name {
    flex: 1;
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 0.8rem;
    color: var(--color-ebony-clay-200, #bbc0d2);
}

.config-file-contents-heading :deep(.g-button.g-transparent) {
    color: var(--color-ebony-clay-200, #bbc0d2);
}

.config-file-contents-heading :deep(.g-button.g-transparent:hover) {
    color: var(--shed-gold);
    background: rgba(255, 255, 255, 0.06);
}

.config-file-contents-body {
    margin: 0;
    padding: 0.85rem 1rem 1rem;
    font-size: 0.85rem;
    line-height: 1.6;
    color: var(--color-ebony-clay-50, #dfe2ea);
    background: none;
    overflow-x: auto;
}
</style>
