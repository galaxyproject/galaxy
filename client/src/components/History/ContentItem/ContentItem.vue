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
                    <b-button class="px-1" title="Delete" size="sm" variant="link" @click.stop="$emit('delete', item)">
                        <span class="fa fa-trash" />
                    </b-button>
                    <b-button
                        v-if="!visible"
                        class="px-1"
                        title="Unhide"
                        size="sm"
                        variant="link"
                        icon="eye-slash"
                        @click.stop="$emit('unhide', item)" />
                    <b-button
                        v-if="deleted"
                        class="px-1"
                        title="Undelete"
                        size="sm"
                        variant="link"
                        icon="trash-restore"
                        @click.stop="$emit('undelete', item)" />
                </div>
                <h5 class="float-left p-1 w-75 font-weight-bold">
                    <div v-if="selectable" class="selector float-left mr-2">
                        <span
                            v-if="selected"
                            class="fa fa-lg fa-check-square-o"
                            @click.stop="$emit('update:selected', false)" />
                        <span v-else class="fa fa-lg fa-square-o" @click.stop="$emit('update:selected', true)" />
                    </div>
                    <span class="id" data-description="id">{{ id }}:</span>
                    <span class="name" data-description="name">{{ name }}</span>
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
        loading() {
            return !this.item;
        },
        selectable() {
            return this.showSelection;
        },
        visible() {
            return this.item.visible;
        },
        deleted() {
            return this.item.isDeleted && !this.item.purged;
        },
        clsState() {
            let state = ContentState[this.item.state];
            if (!state || this.selected) {
                state = "info";
            }
            return `alert-${state}`;
        },
    },
    created() {
    },
};
</script>
<style>
.content-item:hover {
    filter: brightness(105%);
}
</style>
