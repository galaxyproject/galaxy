<template>
    <loading-span v-if="license == null" message="Loading license information"> </loading-span>
    <div v-else-if="license.name" class="text-muted">
        <link itemprop="license" :href="license.licenseId" />
        <span v-if="title">
            {{ title }}
        </span>
        {{ license.name }}
        <a target="_blank" :href="license.url">
            <font-awesome-icon icon="external-link-alt" />
        </a>
        <slot name="buttons"></slot>
    </div>
    <div v-else>
        Unknown License (<i>{{ license.url }}</i
        >)
        <slot name="buttons"></slot>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import LoadingSpan from "components/LoadingSpan";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";

import { faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
library.add(faExternalLinkAlt);

export default {
    components: {
        LoadingSpan,
        FontAwesomeIcon,
    },
    props: {
        licenseId: {
            type: String,
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
