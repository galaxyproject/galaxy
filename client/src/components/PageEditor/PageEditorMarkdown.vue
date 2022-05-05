<template>
    <div id="columns">
        <markdown-editor
            :title="title"
            :markdown-text="markdownText"
            :markdown-config="contentData"
            @onUpdate="onUpdate">
            <template v-slot:buttons>
                <b-button
                    id="save-button"
                    v-b-tooltip.hover.bottom
                    title="Save"
                    variant="link"
                    role="button"
                    @click="saveContent(false)">
                    <font-awesome-icon icon="save" />
                </b-button>
                <b-button
                    id="view-button"
                    v-b-tooltip.hover.bottom
                    title="Save & View"
                    variant="link"
                    role="button"
                    @click="saveContent(true)">
                    <font-awesome-icon icon="eye" />
                </b-button>
            </template>
        </markdown-editor>
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEye, faSave } from "@fortawesome/free-solid-svg-icons";
import MarkdownEditor from "components/Markdown/MarkdownEditor";
import { Toast } from "ui/toast";
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
