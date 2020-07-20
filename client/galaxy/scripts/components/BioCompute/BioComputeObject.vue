<template>
    <div id="bco-viewer" class="overflow-auto h-100" @scroll="onScroll">
        <h2 class="mb-3">
            <span id="invocations-title">BioCompute Object for Invocation {{ invocationId }}</span>
        </h2>
        <bco-header :objectid="object_id" :etag="etag" :specversion="spec_version" />
        <provenance-domain :item="provenance_domain" />
    </div>
</template>

<script>

import axios from "axios";
import {
    getAppRoot
} from "onload/loadConfig";
import BcoHeader from "components/BioCompute/BcoHeader.vue";
import ProvenanceDomain from "components/BioCompute/Provenance.vue";
import { mapActions } from "vuex";

export default {
    name: "BCOviewer",
    components: {
        BcoHeader,
        ProvenanceDomain
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
            object_id: {},
            spec_version: {},
            etag: {},
            provenance_domain: {}
        };
    },
    computed: {
        // ...mapGetters(["getBioComputeById"]),
        // biocomputeState: function () {
        //     const biocompute = this.getBioComputeById(this.invocationId);
        //     return state.biocompute
        // },
    },
    methods: {
        ...mapActions(["cloneBioComputeInfo"]),
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
            const invocationId = this.invocationId;

            // Immediately commit the original BCO to the store.
            context_helper.cloneBioComputeInfo(invocationId);

            // Save the "User" version of the BCO, meaning the version that can be edited
            // by the user by changing inputs on the page but which does NOT affect
            // the originally pulled BCO.  In this way we can compare changes between
            // the original and the edit object.
            //context_helper.fetchIBiocomputeForId(invocationId + '-USER');

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