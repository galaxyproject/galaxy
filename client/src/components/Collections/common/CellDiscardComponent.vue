<script lang="ts">
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import type { ICellRendererParams } from "ag-grid-community";
import { defineComponent, type PropType } from "vue";

export default defineComponent({
    components: {
        FontAwesomeIcon,
    },
    props: {
        // ag-grid-vue3 mounts cell renderers with their params as this prop
        params: { type: Object as PropType<ICellRendererParams>, required: true },
    },
    data() {
        return {
            faTimes,
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
        <FontAwesomeIcon size="2x" :icon="faTimes" @click="onRemove" />
    </div>
</template>

<style lang="scss"></style>
