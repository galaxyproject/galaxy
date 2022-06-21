<template>
    <b-card-group deck>
        <b-card title="BioCompute Object" class="export-plugin-card">
            <p>Learn more about <a href="https://biocomputeobject.org/" target="_blank">BioCompute Objects</a>.</p>
            <a class="bco-json" :href="bcoDownloadLink"><b>Download</b></a>
        </b-card>
        <!-- Add more export plugins here -->
    </b-card-group>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
export default {
    props: {
        invocationId: {
            type: String,
            required: true,
        },
    },
    computed: {
        bcoDownloadLink: function () {
            return `${getAppRoot()}api/invocations/${this.invocationId}/biocompute/download`;
        },
    },
};
</script>
