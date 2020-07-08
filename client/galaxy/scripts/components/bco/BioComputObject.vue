<template>
    <div id="bco-viewer" class="overflow-auto h-100" @scroll="onScroll">
        <h2 class="mb-3">
            <span id="invocations-title">BioCompute Object for Invocation {{ invocationId }}</span>
        </h2>
        <div id="objectid">
            <table>
            	<object-id :item="object_id" />
            </table>
        </div>
        <spec-version :item="spec_version" />
        <e-tag :item="etag" />
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

import { mapCacheActions } from "vuex-cache";
import { mapGetters, mapActions } from "vuex";
import { getRootFromIndexLink } from "onload";

export default {
    name: "BCOviewer",
    components: {
        ObjectId,
        SpecVersion,
        ETag,
    },
    props: {
        invocationId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            treeData: {},
            bco: {},
            object_id: {},
            spec_version: {},
            etag: {},
        };
    },
    computed: {
        ...mapGetters(["getBioComputeById"]),
        biocomputeState: function () {
            const biocompute = this.getBioComputeById(this.invocationId);
            return state.biocompute
        },
        getBCO: function() {
            const invocationId = this.invocationId;
            const url = getAppRoot() + `api/invocations/${invocationId}/export_bco`;

            // Iterator.
            
            // Source:  https://stackoverflow.com/questions/53050116/converting-a-regular-json-file-to-a-parent-child-hierarchical-json-as-used-by-d3
            
            const iterate = (obj) => {
            
                const getObjects = (o, parent) =>
            o && typeof o === 'object' ? Object.entries(o).map(([name, v]) => ({
            name,
            parent,
            children: getObjects(v, name)
            })) : [{
            name: o,
            parent
            }];
        
        	var pc_struct = [obj],
            result = getObjects({ Root: pc_struct[0] }, 'null');
            
            // Kick it back.
            return(result[0]['children']);
    		
            }

            axios
                .get(url)
                .then((response) => {
                    
                    // First, get the tree data in parent/child format.
                    this.treeData = iterate(response.data);
                    
                    // Create a property handler.
                    var this_helper = this;
                    
                    // Now go through and define individual top-level objects.
                    this.treeData.forEach(function (item, index) {
			  this_helper[item['name']] = item;
			});
                    console.log(this);
                })
                .catch((e) => {
                    console.error(e);
                });
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
};
</script>
