<template>
    <b-modal ref="deleteModal" title="Delete History" v-model="showModal" title-tag="h2">
        <p>Delete?</p>
    </b-modal>
</template>

<script>
import { History } from "./model";

export default {
    props: {
        history: { type: History, required: true },
        value: { type: Boolean, required: false, default: false },
    },
    computed: {
        showModal: {
            get() {
                return this.value;
            },
            set(newVal, oldVal) {
                if (newVal !== oldVal) {
                    this.$emit("input", newVal);
                }
            },
        },
    },
};
</script>
