<template>
    <div ref="target" />
</template>

<script>
import GridShared from "mvc/grid/grid-shared";
export default {
    props: {
        actionId: {
            type: String,
            default: null,
        },
        plural: {
            type: String,
            default: null,
        },
        item: {
            type: String,
            default: null,
        },
    },
    mounted() {
        const activeTab = this.actionId == "list_published" ? "shared" : "user";
        new GridShared.View({
            action_id: this.actionId,
            plural: this.plural,
            item: this.item,
            active_tab: activeTab,
        }).$el.appendTo(this.$refs.target);
    },
};
</script>
