<template>
    <span>
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                Page Editor: {{ title }}
                <a id="save-button" class="btn btn-secondary fa fa-save float-right" @click="saveContent"></a>
            </div>
        </div>
        <page-editor-html :page-id="pageId" :content="content" ref="contentEditor" />
    </span>
</template>

<script>
import PageEditorHtml from "./PageEditorHtml";

export default {
    props: {
        pageId: {
            required: true,
            type: String
        },
        content: {
            type: String
        },
        title: {
            type: String
        }
    },
    methods: {
        saveContent: function() {
            this.$refs.contentEditor.saveContent();
        }
    },
    components: {
        PageEditorHtml
    }
};
</script>
