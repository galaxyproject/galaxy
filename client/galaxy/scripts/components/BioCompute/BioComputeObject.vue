<template>
    <div id="bco-viewer" class="overflow-auto h-100" @scroll="onScroll">
        <h2 class="mb-3">
            <span id="invocations-title">BioCompute Object for Invocation {{ invocationId }}</span>
        </h2>
        <bco-header :objectid="bco.object_id" :etag="bco.etag" :specversion="bco.spec_version" />
        <provenance :item="bco.provenance_domain" :invokeId=invocationId />
        <usability-domain :usability="bco.usability_domain" />
    </div>
</template>

<script>

import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import BcoHeader from "components/BioCompute/BcoHeader.vue";
import Provenance from "components/BioCompute/Provenance.vue";
import Usability from "components/BioCompute/Usability.vue";


export default {
    name: "BCOviewer",
    components: {
        BcoHeader,
        Usability,
        Provenance
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
    mounted: function () {
        
        // Call only after everything has loaded.
        // Source: https://vuejs.org/v2/api/#mounted

        // Context helper.
        var context_helper = this;

        this.$nextTick(function () {

            // Define the invocation ID.
            const invocationId = context_helper.invocationId;

            // Fetch the BCO.
            const url = getAppRoot() + `api/invocations/${invocationId}/export_bco`;
            axios.get(url).then((response) => {
                
                // Set the BCO.
                context_helper.bco = response.data;

                // Set the session information.

                // Original values.
                sessionStorage.setItem(invocationId, JSON.stringify(response.data));

                // User-modifiable values.
                sessionStorage.setItem(invocationId + '-USER', JSON.stringify(response.data));

            }).catch((e) => {
                console.error(e);
            });

            // Create a context handler.
            //var this_helper = this;
            
            // Loop over the response and assign values to new
            // objects.
            
            //for (var key of Object.keys(response.data)) {
            
                // Vue-wide object.
                //this_helper[key] = response.data[key]
            //}
            //console.log(this);
            //console.log(this.embargo.start_time);

            
      })
    }
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