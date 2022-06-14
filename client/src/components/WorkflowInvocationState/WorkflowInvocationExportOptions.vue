<template>
    <b-card-group deck>
        <b-card title="BioCompute Object" class="mb-2">
            <p>BioCompute Object description...</p>
            <a class="bco-json" :href="bcoJSON"><b>Download</b></a>
        </b-card>
        <!-- <b-card title="RO-Crate">
                <p>RO-Crate description...</p>
                <a class="bco-json" :href="bcoJSON"><b>Download</b></a>
            </b-card> -->
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
        bcoJSON: function () {
            return `${getAppRoot()}api/invocations/${this.invocationId}/biocompute/download`;
        },
    },
};
</script>
