<template>
    <div>
      <b-modal ref="modal" title="Dataset Selector">
        <p class="my-4">Content</p>
      </b-modal>
    </div>
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
