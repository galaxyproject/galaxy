<script setup lang="ts">
import { computed } from "vue"
import { formatDistanceToNow, parseISO } from "date-fns"

interface RepositoryHealthProps {
    lastUpdated: string
    downloadable: boolean
    installs: number
}

const parsedDate = computed(() => parseISO(`${props.lastUpdated}Z`))
const elapsedTime = computed(() => formatDistanceToNow(parsedDate.value, { addSuffix: true }))
const installableColor = computed(() => (props.downloadable ? "green" : "red"))
const props = defineProps<RepositoryHealthProps>()
</script>
<template>
    <q-fab class="q-px-sm" color="secondary" text-color="primary" icon="troubleshoot" direction="down">
        <q-fab-action color="secondary" text-color="black" icon="download" label="Downlodable">
            <q-badge :color="installableColor" rounded floating />
        </q-fab-action>
        <q-fab-action color="secondary" text-color="black" icon="install_desktop" label="Installs">
            <q-badge rounded color="primary" floating :label="installs" />
        </q-fab-action>
        <q-fab-action color="secondary" text-color="black" icon="event" label="Last Updated">
            <q-badge rounded color="primary" floating :label="elapsedTime" />
        </q-fab-action>
    </q-fab>
</template>
