<template>
    <b-dropdown
        v-if="breadCrumbOptions.length"
        size="sm"
        text="Return to..."
        boundary="viewport"
        data-description="collection breadcrumbs menu"
        no-caret>
        <template v-slot:button-content>
            <Icon icon="arrow-up" class="mr-1" />
            <b class="text-nowrap" v-localize>Return to...</b>
        </template>

        <b-dropdown-item @click="close" data-description="back to history">
            <span>History: {{ history.name }}</span>
        </b-dropdown-item>

        <b-dropdown-item v-for="option in breadCrumbOptions" :key="option.key" @click="reselect(option.value)">
            <span>{{ option.text }}</span>
        </b-dropdown-item>
    </b-dropdown>

    <b-button
        v-else
        class="back"
        size="sm"
        title="`Return to: ${history.name}`"
        @click="close"
        data-description="back to history">
        <Icon icon="arrow-up" class="mr-1" />
        <b class="text-nowrap">Return to: {{ history.name }}</b>
    </b-button>
</template>

<script>
import { History } from "../model";

export default {
    props: {
        history: { type: History, required: true },
        selectedCollections: { type: Array, required: true, validate: (val) => val.length > 0 },
    },
    computed: {
        // List for the dropdown. Should be the history and every parent
        // collection excepting the current one.
        breadCrumbOptions() {
            const parents = this.selectedCollections.slice(0, -1);
            const options = parents.map((bc, i) => {
                return {
                    key: bc.type_id,
                    value: parents.slice(0, i + 1),
                    text: bc.name,
                };
            });
            return options;
        },
    },
    methods: {
        reselect(newList) {
            this.$emit("update:selectedCollections", newList);
        },
        back() {
            const newList = this.selectedCollections.slice(0, -1);
            this.reselect(newList);
        },
        close() {
            this.reselect([]);
        },
    },
};
</script>
