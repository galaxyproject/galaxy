<template>
    <div :class="['content-item m-1 p-0 rounded', clsState]">
        <div class="p-1 cursor-pointer" @click.stop="$emit('update:expanded', !expanded)">
            <div class="overflow-hidden">
                <div class="btn-group float-right">
                    <b-button
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
                        v-if="item.deleted"
                        class="px-1"
                        title="Undelete"
                        size="sm"
                        variant="link"
                        :disabled="item.purged"
                        @click.stop="$emit('undelete', item)">
                        <span class="fa fa-trash-restore" />
                    </b-button>
                    <b-button
                        v-else
                        class="px-1"
                        title="Delete"
                        size="sm"
                        variant="link"
                        @click.stop="$emit('delete', item)">
                        <span class="fa fa-trash" />
                    </b-button>
                    <b-button
                        v-if="!item.visible"
                        class="px-1"
                        title="Unhide"
                        size="sm"
                        variant="link"
                        @click.stop="$emit('unhide', item)">
                        <span class="fa fa-eye-slash" />
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
        <ContentDetails v-if="expanded" :item="item" />
    </div>
</template>

<script>
import ContentDetails from "./ContentDetails";
import ContentState from "./ContentState";
export default {
    components: {
        ContentDetails,
    },
    props: {
        item: { type: Object, required: true },
        id: { type: Number, required: true },
        name: { type: String, required: true },
        expanded: { type: Boolean, required: true },
        selected: { type: Boolean, required: true },
        showSelection: { type: Boolean, required: false, default: false },
        writable: { type: Boolean, required: false, default: true },
    },
    computed: {
        selectable() {
            return this.showSelection;
        },
        clsState() {
            let state = ContentState[this.item.state] || ContentState[this.item.populated_state];
            if (!state || this.selected) {
                state = "info";
            }
            return `alert-${state}`;
        },
    },
    created() {
        if (this.item.history_content_type != "dataset") {
            console.log(this.item);
        }
    },
};
</script>
<style>
.content-item:hover {
    filter: brightness(105%);
}
</style>
