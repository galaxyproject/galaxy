<template>
    <div class="unified-panel-wrapper">
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                <div class="panel-header-buttons">
                    <upload-button></upload-button>
                </div>
                <div class="panel-header-text">Tools</div>
            </div>
        </div>
        <div class="unified-panel-controls">
            <tool-search @results="setResults"/>
        </div>
        <div class="unified-panel-body">
            <div class="toolMenuContainer">
                    <div class="toolMenu">
                        <tool-section v-for="category in toolsLayout" :category="category" :isFiltered="isFiltered"></tool-section>
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
        </div>
    </div>

</template>

<script>
    import ToolSection from './ToolSection';
    import ToolSearch from './ToolSearch';
    import UploadButton from './UploadButton';

    export default {
        name: "ToolBox",
        components: {
            UploadButton,
            ToolSection,
            ToolSearch
        },
        data() {
            return {
                results: null,
            }
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
        computed: {
            isFiltered() {
                if (this.results) {
                    return true;
                } else {
                    return false;
                }
            },
            toolsLayout() {
                if (this.results) {
                    return _.filter(_.map(this.layout, (category) => {
                        return {...category,
                            elems: ((filtered) => {
                                return _.filter(filtered, (el, i) => {
                                    if (el.model_class.endsWith('ToolSectionLabel')) {
                                        return filtered[i + 1] && filtered[i + 1].model_class.endsWith('Tool');
                                    } else {
                                        return true;
                                    }
                                })
                            })(_.filter(category.elems, (el) => {
                                if (el.model_class.endsWith('ToolSectionLabel')) {
                                    return true;
                                } else {
                                    return this.results.includes(el.id);
                                }
                            }))
                        }
                    }), (category) => {
                        return category.elems.length ||
                            (category.model_class.endsWith('Tool') && this.results.includes(category.id));
                    });
                } else {
                    return this.layout;
                }
            }
        },
        created() {

        },
        methods: {
            setResults(results) {
                this.results = results;
            }
        }
    };
</script>

<style scoped>
    .unified-panel-wrapper {
        display: flex;
        flex-flow: column;
        height: 100%;
    }
</style>