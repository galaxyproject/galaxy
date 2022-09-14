<template>
    <loading-span v-if="license == null" message="Loading license information"> </loading-span>
    <span v-else-if="license.name" class="text-muted">
        <link itemprop="license" :href="license.licenseId" />
        <span v-if="title">
            {{ title }}
        </span>
        <external-link :href="license.url">
            {{ license.name }}
        </external-link>
        <slot name="buttons"></slot>
    </span>
    <span v-else>
        Unknown License (<i>{{ license.url }}</i
        >)
        <slot name="buttons"></slot>
    </span>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import LoadingSpan from "components/LoadingSpan";
import ExternalLink from "components/ExternalLink";

export default {
    components: {
        LoadingSpan,
        ExternalLink,
    },
    props: {
        licenseId: {
            type: String,
            required: true,
        },
        inputLicenseInfo: {
            type: Object,
            required: false,
        },
        title: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            license: this.inputLicenseInfo,
        };
    },
    watch: {
        licenseId: function (newLicense, oldLicense) {
            if (newLicense != oldLicense) {
                this.fetchLicense();
            }
        },
    },
    created() {
        if (this.license == null) {
            this.fetchLicense();
        }
    },
    methods: {
        fetchLicense() {
            this.license = null;
            const url = `${getAppRoot()}api/licenses/${this.licenseId}`;
            axios
                .get(url)
                .then((response) => response.data)
                .then((data) => {
                    this.license = data;
                });
        },
    },
};
</script>

<style></style>
