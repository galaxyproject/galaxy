<template>
    <span>
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                Page Editor: {{ title }}
                <a id="save-button" class="btn btn-secondary fa fa-save float-right"></a>
            </div>
        </div>
        <page-editor-html :page-id="pageId" :content="content" />
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
    components: {
        PageEditorHtml
    },
}
</script>
