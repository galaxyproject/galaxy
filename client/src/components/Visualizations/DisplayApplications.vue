<template>
    <div>
        <UrlDataProvider :url="url" v-slot="{ result: dataset, loading }">
            <b-alert v-if="dataset && dataset.display_apps && dataset.display_apps.length > 0" variant="info" show>
                You may visualize your dataset using the following external links:
                <div class="p-2">
                    <div v-for="(displayApp, displayKey) in dataset.display_apps" :key="displayKey">
                        <span class="font-weight-bold">{{ displayKey + 1 }}. {{ displayApp.label }}</span>
                        <span v-for="(link, linkKey) in displayApp.links" :key="linkKey">
                            <span v-if="linkKey == 0">(</span>
                            <b-link :href="link.href" :target="link.target" variant="primary" size="sm">{{
                                link.text
                            }}</b-link>
                            <span v-if="linkKey != displayApp.links.length - 1">, </span>
                            <span v-else>)</span>
                        </span>
                    </div>
                </div>
                <div>or select a local visualization from below.</div>
            </b-alert>
        </UrlDataProvider>
    </div>
</template>
<script>
import { UrlDataProvider } from "components/providers/UrlDataProvider";
export default {
    components: {
        UrlDataProvider,
    },
    props: {
        datasetId: {
            type: String,
            required: true,
        },
    },
    computed: {
        url() {
            return `api/datasets/${this.datasetId}`;
        },
    },
};
</script>
