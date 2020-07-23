<template>
    <div id="bco-viewer" class="overflow-auto h-100" @scroll="onScroll">
        <h2 class="mb-3">
            <span id="invocations-title">BioCompute Object for Invocation {{ invocationId }}</span>
        </h2>
        <bco-header :objectid="bco.object_id" :etag="bco.etag" :specversion="bco.spec_version" />
        <usability :usability="bco.usability_domain" />
        <span> {{ bco }} </span>
        <!-- <provenance-domain :item="bco.provenance_domain" /> -->
    </div>
</template>

<script>

import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import BcoHeader from "components/BioCompute/BcoHeader.vue";
import Usability from "components/BioCompute/Usability.vue";
// import ProvenanceDomain from "components/BioCompute/Provenance.vue";


export default {
    name: "BCOviewer",
    components: {
        BcoHeader,
        Usability,
        // ProvenanceDomain
    },
    props: {
        invocationId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            bco: {},
        };
    },
    created() {
        const invocationId = this.invocationId;
        const url = getAppRoot() + `api/invocations/${this.invocationId}/export_bco`;
        axios.get(url).then((response) => {
            this.bco = response.data}).catch((e) => {
                    console.error(e);
                });
        return this.bco
    },
    methods: {
        onScroll({
            target: {
                scrollTop,
                clientHeight,
                scrollHeight
            }
        }) {
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
<style>
	
	/* Don't want the table cells to be too wide (forces text-wrapping) */

	button {
		width: 100%;
	}

    h2 {
        font-weight: bold;
        margin-top: 20px;
    }

	td {
		border-bottom: 1px solid #D3D3D3;
	}

	td {
		max-width: 350px;
		padding: 5px;
	}

    td:nth-child(1) {
        font-weight: bold;
    }

    td.bold_except {
        font-weight: normal;
    }

    td.bold_contain {
        font-weight: bold;
    }

    td.border_except {
        border-bottom: none;
    }

	textarea {
        padding: 5px;
		resize: none;
	}

</style>