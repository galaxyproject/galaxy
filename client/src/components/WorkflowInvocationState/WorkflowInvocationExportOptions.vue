<template>
    <b-card-group deck>
        <b-card title="BioCompute Object" class="export-plugin-card">
            <p>
                A BioCompute Object (BCO) is the unofficial name for a JSON object that adheres to the
                <a href="https://standards.ieee.org/ieee/2791/7337/">IEEE-2791-2020 standard</a>. A BCO is designed to
                communicate High-throughput Sequencing (HTS) analysis results, data set creation, data curation, and
                bioinformatics verification protocols.
            </p>
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
