<template>
    <b-modal v-model="modalShow" ref="modal" title="Dataset Selector">
        <p class="my-4">Content</p>
    </b-modal>
</template>

<script>
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    props: {},
    computed: {},
    data() {
        return {
            modalShow: true
        };
    },
    created: function() {},
    updated: function() {},
    methods: {}
};
</script>
