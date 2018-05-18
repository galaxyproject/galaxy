<template>
    <div>
      <b-btn v-b-modal.modal1>Launch demo modal</b-btn>

      <!-- Modal Component -->
      <b-modal id="modal1" title="Bootstrap-Vue">
        <p class="my-4">Hello from modal!</p>
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
    }
};
</script>
