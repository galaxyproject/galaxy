<template>
    <b-dropdown-item class="ml-1" :title="title" :data-panel-id="panelView.id" :active="isSelected" @click="onClick">
        <span :class="['fa', `fa-${icon}`]" fixed-width />
        <span v-localize>{{ name }}</span>
    </b-dropdown-item>
</template>

<script>
import { types_to_icons } from "../utilities";

export default {
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
    computed: {
        title() {
            return this.panelView.description;
        },
        icon() {
            const viewType = this.panelView.view_type;
            if (this.isSelected) {
                return "check";
            } else {
                return types_to_icons[viewType] || "eye";
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
