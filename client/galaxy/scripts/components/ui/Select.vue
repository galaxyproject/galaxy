<template>
  <v-select
    :label="label"
    :options="options"
    v-model="selected">
    <template slot="no-options">No matches found</template>
  </v-select>
</template>

<script>
import Vue from 'vue';
import VueSelect from 'vue-select';

Vue.component('v-select', VueSelect);

export default {
  props: {
    label: {
      type: String
    },
    options: {
      type: Array
    },
    value: {
      type: Object
    }
  },
  data () {
    return {
      selected: this.value
    }
  },
  watch: {
    selected (value) {
      this.$emit('input', value);
    }
  }
}
</script>

<style>
  .v-select .dropdown-toggle {
    border: 1px solid #aaa;
  }

  .v-select .dropdown-menu {
    padding: 0;
  }

  .v-select .dropdown-menu > .highlight > a {
    background: #3975d7;
  }

  .v-select .dropdown-toggle .clear {
    visibility: hidden;
  }
</style>
