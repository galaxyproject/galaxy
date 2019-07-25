<template>
    <div>
        <hr />
        <div>The new Vue tools panel</div>
        <hr />

            <div class="toolMenu">
                <tool-section v-for="category in layout" :category="category"></tool-section>
            </div>
            <div class="toolSectionPad"></div>
            <div class="toolSectionPad"></div>

            <div class="toolSectionTitle" id="title_XXinternalXXworkflow">
                <a>{{ workflowsTitle }}</a>
            </div>
            <div id="internal-workflows" class="toolSectionBody">
                <div class="toolSectionBg"></div>

                <div class="toolTitle" v-for="workflow in workflows">
                    <a :href="workflow.href">
                        {{ workflow.title }}
                    </a>
                </div>
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
      workflowsTitle: {
        type: String
      },
      workflows: {
        type: Array
      }
    },
    created() {
      console.log('layout', this.layout);
    }
  };
</script>

<style scoped>

</style>