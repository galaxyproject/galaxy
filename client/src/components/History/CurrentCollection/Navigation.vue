<template>
    <b-breadcrumb>
        <b-breadcrumb-item href="#" @click="close">
            <span class="fa fa-angle-double-left" />
        </b-breadcrumb-item>
        <b-breadcrumb-item v-for="option in breadCrumbOptions" :key="option.key" @click="reselect(option.value)">
            <span>{{ option.text }}</span>
        </b-breadcrumb-item>
    </b-breadcrumb>
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
