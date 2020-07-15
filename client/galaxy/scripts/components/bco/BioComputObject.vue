<style>
	
	/* Don't want the table cells to be too wide (forces text-wrapping) */

	button {
		width: 100%;
	}

	tr {
		border-bottom: 1px solid #D3D3D3;
	}

	td {
		max-width: 350px;
		padding: 5px;
	}

	textarea {
		resize: none;
	}

</style>

<template>
    <div id="bco-viewer" class="overflow-auto h-100" @scroll="onScroll">
        <h2 class="mb-3">
            <span id="invocations-title">BioCompute Object for Invocation {{ invocationId }}</span>
        </h2>
        <object-id :item="object_id" />
        <spec-version :item="spec_version" />
        <e-tag :item="etag" />
        <h2>Provenance Domain</h2>
        <provenance-domain :item="provenance_domain" />
    </div>
</template>

<script>

import axios from "axios";
import {
    getAppRoot
} from "onload/loadConfig";
import ObjectId from "components/bco/ObjectId.vue";
import SpecVersion from "components/bco/SpecVersion.vue";
import ETag from "components/bco/ETag.vue";
import ProvenanceDomain from "components/bco/Provenance.vue";

import { mapCacheActions } from "vuex-cache";
import { mapGetters, mapActions } from "vuex";
import { getRootFromIndexLink } from "onload";

export default {
    name: "BCOviewer",
    components: {
        ObjectId,
        SpecVersion,
        ETag,
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
        ...mapGetters(["getBioComputeById"]),
        biocomputeState: function () {
            const biocompute = this.getBioComputeById(this.invocationId);
            return state.biocompute
        },
    },
    methods: {
        ...mapActions(["fetchIBiocomputeForId"]),
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

        this.$nextTick(function () {
        const invocationId = this.invocationId;
        const url = getAppRoot() + `api/invocations/${invocationId}/export_bco`;

        axios
            .get(url)
            .then((response) => {
                
                // Create a property handler.
                var this_helper = this;
                
                // Loop over the response and assign values to new
                // objects.
                
                for (var key of Object.keys(response.data)) {
                
                    // Vue-wide object.
                    this_helper[key] = response.data[key]
                }

                console.log(this);
                console.log(this.embargo.start_time);
    
            })
            .catch((e) => {
                console.error(e);
            });
      })
    }
};
</script>
