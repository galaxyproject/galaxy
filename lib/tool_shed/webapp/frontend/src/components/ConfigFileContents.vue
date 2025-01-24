<script setup lang="ts">
import { copyAndNotify, notify } from "@/util"

import { exportFile } from "quasar"

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
                <q-btn size="sm" flat dense icon="content_copy" @click="copyContents" />
                <q-btn size="sm" flat dense icon="download" @click="downloadContents" />
            </div>
            <pre style="border-left: 1px solid gray; padding-left: 10px">{{ contents }}</pre>
        </q-card-section>
    </q-card>
</template>
