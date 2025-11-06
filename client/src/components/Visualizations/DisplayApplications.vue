<script setup lang="ts">
import { defineProps } from "vue";

import { DatasetProvider } from "@/components/providers";

interface LinkType {
    app_name: string;
    link_name: string;
}

const props = defineProps({
    datasetId: {
        type: String,
        required: true,
    },
});
function getUrl(link: LinkType) {
    return `/display_applications/${props.datasetId}/${link.app_name}/${link.link_name}`;
}
</script>
<template>
    <div>
        <DatasetProvider :id="props.datasetId" v-slot="{ result: dataset }">
            <b-alert
                v-if="
                    (dataset && dataset.display_apps && dataset.display_apps.length > 0) ||
                    (dataset && dataset.display_types && dataset.display_types.length > 0)
                "
                variant="info"
                show>
                You can display your dataset with the following links:
                <div class="p-2">
                    <ol>
                        <li v-for="(displayApp, displayKey) in dataset.display_apps" :key="`display-app-${displayKey}`">
                            <span class="font-weight-bold">{{ displayApp.label }}</span>
                            <span v-for="(link, linkKey) in displayApp.links" :key="`display-app-link-${linkKey}`">
                                <span v-if="linkKey == 0">(</span>
                                <router-link :to="getUrl(link)">{{ link.text }}</router-link>
                                <span v-if="linkKey != displayApp.links.length - 1">, </span>
                                <span v-else>)</span>
                            </span>
                        </li>
                        <li
                            v-for="(displayType, displayKey) in dataset.display_types"
                            :key="`display-type-${displayKey}`">
                            <span class="font-weight-bold">{{ displayType.label }}</span>
                            <span v-for="(link, linkKey) in displayType.links" :key="`display-type-link-${linkKey}`">
                                <span v-if="linkKey == 0">(</span>
                                <a :href="link.href">{{ link.text }}</a>
                                <span v-if="linkKey != displayType.links.length - 1">, </span>
                                <span v-else>)</span>
                            </span>
                        </li>
                    </ol>
                </div>
                <div>or select a visualization from below.</div>
            </b-alert>
        </DatasetProvider>
    </div>
</template>
