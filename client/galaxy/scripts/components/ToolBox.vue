<template>
    <div>
        <hr />
        <div>The new Vue tools panel</div>
        <hr />

            <div class="toolMenu">
                <tool-section v-for="category in layout" :category="category"></tool-section>
            </div>
    </div>

</template>

<script>
  import ToolSection from './ToolSection';

  export default {
    name: "ToolBox",
    components: {
      ToolSection
    },
    props: {
      tools: {
        type: Array,
      },
      layout: {
        type: Array,
      },
      toolSearch: {
        type: Object,
      },
    },
    created() {
      console.log('layout', this.layout);
    }
  };
</script>

<style scoped>

</style>