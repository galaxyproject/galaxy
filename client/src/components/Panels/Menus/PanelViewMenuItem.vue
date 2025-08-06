<template>
    <BDropdownItem class="ml-1" :title="title" :data-panel-id="panelView.id" :active="isSelected" @click="onClick">
        <FontAwesomeIcon :icon="icon" data-description="panel view item icon" fixed-width />
        <span v-localize>{{ name }}</span>
    </BDropdownItem>
</template>

<script>
import { faCheck, faEye } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdownItem } from "bootstrap-vue";

import { types_to_icons } from "../utilities";

export default {
    components: {
        BDropdownItem,
        FontAwesomeIcon,
    },
    props: {
        currentPanelView: {
            type: String,
            required: true,
        },
        panelView: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            faCheck,
            faEye,
        };
    },
    computed: {
        title() {
            return this.panelView.description;
        },
        icon() {
            const viewType = this.panelView.view_type;
            if (this.isSelected) {
                return this.faCheck;
            } else {
                return types_to_icons[viewType] || this.faEye;
            }
        },
        isSelected() {
            return this.currentPanelView == this.panelView.id;
        },
        name() {
            return this.panelView.name;
        },
    },
    methods: {
        onClick() {
            this.$emit("onSelect", this.panelView);
        },
    },
};
</script>
