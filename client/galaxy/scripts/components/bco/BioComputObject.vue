<template>
    <div id="bco-viewer" class="overflow-auto h-100" @scroll="onScroll">
        <h2 class="mb-3">
            <span id="invocations-title">BioCompute Object</span>
        </h2>
        <json-dump class="item" :item="treeData" />
    </div>
</template>

<script>

import axios from "axios";

import { mapActions } from "vuex";
import { getAppRoot } from "onload/loadConfig";
import JsonDump from "components/bco/JsonDump.vue";

export default {
    name: "BCOviewer",
    components: {
        JsonDump,
    },
    props: {
        invocationId: {
            type: String,
            required: true,
        },
    },
    data: function () {
        return {
            treeData: {},
        };
    },
    computed: {
        getBCO: function () {
            const invocationId = this.invocationId;
            const url = getAppRoot() + `api/invocations/${invocationId}/export_bco`;
            // const params = {};

            axios
                .get(url)
                .then((response) => {
                    this.treeData = response.data;
                })
                .catch((e) => {
                    console.error(e);
                });
        },
    },
    methods: {
        onScroll({ target: { scrollTop, clientHeight, scrollHeight } }) {
            if (scrollTop + clientHeight >= scrollHeight) {
                if (this.offset + this.limit <= this.rows.length) {
                    this.offset += this.limit;
                    this.load(true);
                }
            }
        },
    },
};
</script>
