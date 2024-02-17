<template>
    <MarkdownEditor
        :title="title"
        :markdown-text="markdownText"
        :markdown-config="contentData"
        mode="page"
        @onUpdate="onUpdate">
        <template v-slot:buttons>
            <b-button
                id="save-button"
                v-b-tooltip.hover.bottom
                title="Save"
                variant="link"
                role="button"
                @click="saveContent(false)">
                <FontAwesomeIcon icon="save" />
            </b-button>
            <b-button
                id="view-button"
                v-b-tooltip.hover.bottom
                title="Save & View"
                variant="link"
                role="button"
                @click="saveContent(true)">
                <FontAwesomeIcon icon="eye" />
            </b-button>
        </template>
    </MarkdownEditor>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEye, faSave } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import BootstrapVue from "bootstrap-vue";
import MarkdownEditor from "components/Markdown/MarkdownEditor";
import { Toast } from "composables/toast";
import Vue from "vue";

import { save } from "./util";

Vue.use(BootstrapVue);

library.add(faEye, faSave);

export default {
    components: {
        MarkdownEditor,
        FontAwesomeIcon,
    },
    props: {
        pageId: {
            required: true,
            type: String,
        },
        publicUrl: {
            required: true,
            type: String,
        },
        title: {
            type: String,
            default: null,
        },
        content: {
            type: String,
            default: null,
        },
        contentData: {
            type: Object,
            default: null,
        },
    },
    data: function () {
        return {
            markdownText: this.content,
        };
    },
    methods: {
        onUpdate(newContent) {
            this.markdownText = newContent;
        },
        saveContent(showResult) {
            save(this.pageId, this.markdownText, !showResult)
                .then(() => {
                    if (showResult) {
                        window.location = this.publicUrl;
                    }
                })
                .catch((error) => {
                    Toast.error(`Failed to save page: ${error}`);
                });
        },
    },
};
</script>
