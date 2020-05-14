<template>
    <div id="bco-viewer" class="overflow-auto h-100" @scroll="onScroll">
        <h2 class="mb-3">
            <span id="invocations-title">BioCompute Object</span>
        </h2>
        <top-level :bco="bco" />
        <provenance :bco="bco" />
        <usability :bco="bco" />
        <extension :bco="bco" />
        <description :bco="bco" />
        <parametric :bco="bco" />
        <inputoutput :bco="bco" />
        <error-domain :bco="bco" />
    </div>
</template>

<script>
import axios from "axios";

import { mapActions } from "vuex";
import { getAppRoot } from "onload/loadConfig";
import TopLevel from "components/bco/TopLevel.vue";
import Provenance from "components/bco/Provenance.vue";
import Usability from "components/bco/Usability.vue";
import Extension from "components/bco/Extension.vue";
import Parametric from "components/bco/Parametric.vue";
import Description from "components/bco/Description.vue";
import Inputoutput from "components/bco/InputOutput.vue";
import ErrorDomain from "components/bco/ErrorDomain.vue";

export default {
    name: "BCOviewer",
    components: {
        TopLevel,
        Provenance,
        Usability,
        Extension,
        Description,
        Parametric,
        Inputoutput,
        ErrorDomain,
    },
    props: {
        invocationId: {
            type: String,
            required: true,
        },
    },
    data: function () {
        return {
            bco: {},
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
                    this.bco = response.data;
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
