<template>
    <div>
        <DatasetProvider :id="datasetId" v-slot="{ result: dataset }">
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
                        <li v-for="(displayApp, displayKey) in dataset.display_apps" :key="displayKey">
                            <span class="font-weight-bold">{{ displayApp.label }}</span>
                            <span v-for="(link, linkKey) in displayApp.links" :key="linkKey">
                                <span v-if="linkKey == 0">(</span>
                                <b-link :href="link.href" :target="link.target">{{ link.text }}</b-link>
                                <span v-if="linkKey != displayApp.links.length - 1">, </span>
                                <span v-else>)</span>
                            </span>
                        </li>
                        <li v-for="(displayType, displayKey) in dataset.display_types" :key="displayKey">
                            <span class="font-weight-bold">{{ displayType.label }}</span>
                            <span v-for="(link, linkKey) in displayType.links" :key="linkKey">
                                <span v-if="linkKey == 0">(</span>
                                <b-link :href="link.href" :target="link.target">{{ link.text }}</b-link>
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
<script>
import { DatasetProvider } from "components/providers";
export default {
    components: {
        DatasetProvider,
    },
    props: {
        datasetId: {
            type: String,
            required: true,
        },
    },
};
</script>
