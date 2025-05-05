<script lang="ts">
/* cannot use a setup block and get params injection in Vue 2.7 I think */

import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { type ICellRendererParams } from "ag-grid-community";
import { defineComponent } from "vue";

library.add(faTimes);

export default defineComponent({
    components: {
        FontAwesomeIcon,
    },
    data() {
        return {
            params: {} as ICellRendererParams,
        };
    },
    computed: {},
    methods: {
        onRemove() {
            this.params.context.onRemove(this.params.data.datasets);
        },
    },
});
</script>
<template>
    <div>
        <FontAwesomeIcon size="2x" icon="fa-times" @click="onRemove" />
    </div>
</template>

<style lang="scss"></style>
