<template>
    <div :class="['content-item m-1 p-0 rounded', clsStatus]">
        <div class="p-1 cursor-pointer" @click.stop="onClick">
            <div class="overflow-hidden">
                <div class="btn-group float-right">
                    <b-button
                        v-if="expandable"
                        class="px-1"
                        title="Display"
                        size="sm"
                        variant="link"
                        @click.stop="$emit('display', item)">
                        <span class="fa fa-eye" />
                    </b-button>
                    <b-button class="px-1" title="Edit" size="sm" variant="link" @click.stop="$emit('edit', item)">
                        <span class="fa fa-pencil" />
                    </b-button>
                    <b-button
                        v-if="writeable && item.deleted"
                        class="px-1"
                        title="Undelete"
                        size="sm"
                        variant="link"
                        :disabled="item.purged"
                        @click.stop="$emit('undelete', item)">
                        <span class="fa fa-trash-restore" />
                    </b-button>
                    <b-button
                        v-else-if="writeable"
                        class="px-1"
                        title="Delete"
                        size="sm"
                        variant="link"
                        @click.stop="$emit('delete', item)">
                        <span class="fa fa-trash" />
                    </b-button>
                    <b-button
                        v-if="writeable && !item.visible"
                        class="px-1"
                        title="Unhide"
                        size="sm"
                        variant="link"
                        @click.stop="$emit('unhide', item)">
                        <span class="fa fa-unlock" />
                    </b-button>
                </div>
                <h5 class="float-left p-1 w-75 font-weight-bold">
                    <div v-if="selectable" class="selector float-left mr-2">
                        <span
                            v-if="selected"
                            class="fa fa-lg fa-check-square-o"
                            @click.stop="$emit('update:selected', false)" />
                        <span v-else class="fa fa-lg fa-square-o" @click.stop="$emit('update:selected', true)" />
                    </div>
                    <span class="id">{{ id }}:</span>
                    <span class="name">{{ name }}</span>
                    <h6 v-if="item.collection_type" class="description py-1">
                        a {{ item.collection_type }} with {{ item.element_count }} items
                    </h6>
                </h5>
            </div>
        </div>
        <ContentDetails v-if="expanded" @edit="$emit('edit', $event)" :item="item" />
    </div>
</template>

<script>
import ContentDetails from "./ContentDetails";
import ContentStatus from "./ContentStatus";
export default {
    components: {
        ContentDetails,
    },
    props: {
        item: { type: Object, required: true },
        id: { type: Number, required: true },
        name: { type: String, required: true },
        state: { type: String, default: null },
        expanded: { type: Boolean, required: true },
        selected: { type: Boolean, default: false },
        expandable: { type: Boolean, default: true },
        selectable: { type: Boolean, default: false },
        writeable: { type: Boolean, default: true },
    },
    computed: {
        clsStatus() {
            const status = ContentStatus[this.state];
            if (!status || this.selected) {
                return "alert-info";
            } else {
                return `alert-${status}`;
            }
        },
    },
    methods: {
        onClick() {
            if (this.expandable) {
                this.$emit("update:expanded", !this.expanded);
            } else {
                this.$emit("drilldown", this.item);
            }
        },
    },
};
</script>
<style>
.content-item:hover {
    filter: brightness(105%);
}
.content-item {
    .name {
        word-wrap: break-word;
    }
}
</style>
