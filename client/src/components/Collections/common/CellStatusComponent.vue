<script lang="ts">
import { faCheck, faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import type { ICellRendererParams } from "ag-grid-community";
import { defineComponent, type PropType } from "vue";

import GPopover from "@/components/BaseComponents/GPopover.vue";

export default defineComponent({
    components: {
        GPopover,
        FontAwesomeIcon,
    },
    props: {
        // ag-grid-vue3 mounts cell renderers with their params as this prop
        params: { type: Object as PropType<ICellRendererParams>, required: true },
    },
    data() {
        return {
            faCheck,
            faExclamationTriangle,
        };
    },
    computed: {
        id() {
            return `status-for-identifier-${this.params.data.id}`;
        },
        isDuplicate() {
            return this.params.value == "duplicate";
        },
        requiresPairing() {
            return this.params.value == "requires_pairing";
        },
        statusClass() {
            if (this.isDuplicate || this.requiresPairing) {
                return "status-warn";
            } else {
                return "status-ok";
            }
        },
        popoverContent() {
            if (this.isDuplicate) {
                return "This element has a duplicate identifier with another element, please edit one or the other by double clicking on the identifier value in the table and changing it.";
            } else if (this.requiresPairing) {
                return "This dataset must be paired or it will not be included in the final list.";
            } else {
                return "This element is ok and will be included in the generated list.";
            }
        },
        icon() {
            if (this.isDuplicate || this.requiresPairing) {
                return this.faExclamationTriangle;
            } else {
                return this.faCheck;
            }
        },
    },
    methods: {},
});
</script>
<template>
    <div :class="statusClass">
        <FontAwesomeIcon :id="id" size="2x" :icon="icon" />
        <GPopover :target="id" title="Status" triggers="hover focus" :content="popoverContent"></GPopover>
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.status-ok {
    color: $brand-success;
}

.status-warn {
    color: $brand-warning;
}
</style>
