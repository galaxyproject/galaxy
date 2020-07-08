<template>
    <div id="bco-viewer" class="overflow-auto h-100" @scroll="onScroll">
        <h2 class="mb-3">
            <span id="invocations-title">BioCompute Object for Invocation {{ invocationId }}</span>
        </h2>
        <ul>
            <json-dump class="item" :item="treeData" />
        </ul>
    </div>
</template>

<script>

import axios from "axios";
import {
    getAppRoot
} from "onload/loadConfig";
import JsonDump from "components/bco/JsonDump.vue";

import { mapCacheActions } from "vuex-cache";
import { mapGetters, mapActions } from "vuex";
import { getRootFromIndexLink } from "onload";

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
    data() {
        return {
            treeData: {},
            bco: {},
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
            
            // Get rid of the root element, converting the array
            // into an object.
            
            // Source:  https://stackoverflow.com/questions/7193599/how-can-i-turn-a-jsonarray-into-a-jsonobject
            
            //JSONObject jo = new JSONObject();
            
        // Populate the array.
        //for(var i in result[0]) {
        
            //jo.put(i, result[0]);
        
        //}
            
            // Kick it back.
            console.log(result[0]);
            return(result[0]);
            
            //return(jo);
            
            }

            axios
                .get(url)
                .then((response) => {
                    this.treeData = iterate(response.data);
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
