<script setup lang="ts">
import { GButton } from "@galaxyproject/galaxy-ui"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faCopy, faDownload } from "@fortawesome/free-solid-svg-icons"
import { copyAndNotify, downloadTextFile, notify } from "@/util"

import PreformattedContent from "@/components/PreformattedContent.vue"

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
        <div class="config-file-contents-section">
            <div class="config-file-contents-heading">
                {{ name }}
                <GButton icon-only transparent aria-label="Copy contents" @click="copyContents">
                    <FontAwesomeIcon :icon="faCopy" />
                </GButton>
                <GButton icon-only transparent aria-label="Download" @click="downloadContents">
                    <FontAwesomeIcon :icon="faDownload" />
                </GButton>
            </div>
            <preformatted-content :contents="contents" />
        </div>
    </section>
</template>

<style scoped>
.config-file-contents {
    margin: var(--spacing-2);
    background-color: var(--background-color);
    border: 1px solid var(--color-grey-300);
    border-radius: 0.25rem;
}

.config-file-contents-section {
    padding: var(--spacing-4);
    padding-top: var(--spacing-1);
}

.config-file-contents-heading {
    display: flex;
    align-items: center;
    gap: var(--spacing-1);
    font-size: var(--font-size-small);
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
</style>
