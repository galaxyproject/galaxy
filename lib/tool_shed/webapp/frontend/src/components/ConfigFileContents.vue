<script setup lang="ts">
import { GButton } from "@galaxyproject/galaxy-ui"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faCopy, faDownload } from "@fortawesome/free-solid-svg-icons"
import { copyAndNotify, notify } from "@/util"

import { exportFile } from "quasar"
import PreformattedContent from "@/components/PreformattedContent.vue"

interface ConfigFileContentsProps {
    name: string
    contents: string
    what: string
}

async function copyContents() {
    copyAndNotify(props.contents, `${props.what} copied to your clipboard`)
}

async function downloadContents() {
    const status = exportFile(props.name, props.contents)
    if (!status) {
        notify("Your browser does not allow this operation")
    }
}

const props = defineProps<ConfigFileContentsProps>()
</script>
<template>
    <q-card flat bordered class="q-ma-sm">
        <q-card-section class="q-pt-xs">
            <div class="text-overline">
                {{ name }}
                <GButton icon-only transparent aria-label="Copy contents" @click="copyContents">
                    <FontAwesomeIcon :icon="faCopy" />
                </GButton>
                <GButton icon-only transparent aria-label="Download" @click="downloadContents">
                    <FontAwesomeIcon :icon="faDownload" />
                </GButton>
            </div>
            <preformatted-content :contents="contents" />
        </q-card-section>
    </q-card>
</template>
