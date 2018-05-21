<template>
    <b-modal ref="modal" title="Dataset Selector">
        <p class="my-4">Content</p>
    </b-modal>
</template>

<script>
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    props: {
    },
    computed: {
    },
    data() {
        return {
        };
    },
    created: function() {
        this.show();
    },
    updated: function() {
    },
    methods: {
        show() {
          this.$refs.modal.show()
        },
        hide() {
          this.$refs.modal.hide()
        }
    }
};
</script>
