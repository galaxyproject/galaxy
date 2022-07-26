<template>
    <span v-if="decoded_id">({{ decoded_id }})</span>
</template>
<script>
import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";

export default {
    props: {
        id: {
            type: String,
            required: true,
        },
    },
    data() {
        return { decoded_id: null };
    },
    computed: {
        isAdmin() {
            // window.parent.Galaxy is needed when instance is mounted in mako
            const Galaxy = getGalaxyInstance() || window.parent.Galaxy;
            return Galaxy?.user?.isAdmin() || false;
        },
    },
    created: function () {
        this.decodeId(this.id);
    },
    methods: {
        decodeId: async function (id) {
            if (this.isAdmin) {
                const url = `${getAppRoot()}api/configuration/decode/${id}`;
                try {
                    const response = await axios.get(url);
                    this.decoded_id = response.data.decoded_id;
                } catch (e) {
                    rethrowSimple(e);
                }
            }
        },
    },
};
</script>
