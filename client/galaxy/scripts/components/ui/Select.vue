<template>
  <multiselect
      preselectFirst
      v-model="selected"
      :options="options"
      :label="label"
      :loading="loading"
      :disabled="disabled"
      :placeholder="placeholder"
      :show-labels="false"
      :allow-empty="false"
      :option-height="32">
      <span slot="noResult">No matches found.</span>
    </multiselect>
</template>

<script>
import Multiselect from "vue-multiselect";
import "vue-multiselect/dist/vue-multiselect.min.css";

export default {
  props: [
    "label",
    "value",
    "options",
    "loading",
    "disabled",
    "placeholder"
  ],
  components: {
    Multiselect
  },
  data () {
    return {
      selected: this.value
    }
  },
  watch: {
    selected (value) {
      this.$emit("input", value);
    }
  }
}
</script>

<style>
  .multiselect {
    font-size: 12px;
    min-height: 32px;
  }

  .multiselect__single {
    font-size: 12px;
    margin-bottom: 0;
    line-height: 30px;
  }

  .multiselect__select {
    width: 26px;
    height: 30px;
  }

  .multiselect__tags {
    padding-top: 0;
    padding-left: 0;
    min-height: 32px;
  }

  .multiselect__tags,
  .multiselect__content-wrapper,
  .multiselect--above .multiselect__content-wrapper {
    border-color: #aaa;
  }

  .multiselect__spinner {
    width: 26px;
    height: 30px;
    border-radius: 5px;
  }

  .multiselect__spinner:after,
  .multiselect__spinner:before {
    border-color: #d29300 transparent transparent;
  }

  .multiselect__input {
    font-size: 12px !important;
    line-height: 24px !important;
    padding-left: 5px !important;
    margin-bottom: 0;
    border: none !important;
  }

  .multiselect__option {
    padding: 8px;
    min-height: 26px;
    line-height: 12px;
  }

  .multiselect__option--highlight,
  .multiselect__option--selected.multiselect__option--highlight {
    background: #3875d7;
  }
</style>
