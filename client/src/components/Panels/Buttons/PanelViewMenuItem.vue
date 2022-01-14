<template>
    <b-dropdown-item
        :active="currentPanelView == panelView.id"
        :disabled="currentPanelView == panelView.id"
        :data-panel-id="panelView.id"
        @click="onClick">
        <span :class="icon" />
        <span :title="title" v-localize>{{ name }}</span>
    </b-dropdown-item>
</template>

<script>
const types_to_icons = {
    default: "fa-backspace",
    generic: "fa-filter",
    ontology: "fa-sitemap",
    activity: "fa-project-diagram",
    publication: "fa-newspaper",
    training: "fa-graduation-cap",
};

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
            const faIcon = types_to_icons[viewType];
            return ["fa", faIcon];
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
