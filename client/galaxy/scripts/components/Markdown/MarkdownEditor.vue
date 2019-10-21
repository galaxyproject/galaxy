<template>
    <textarea class="markdown-textarea" id="workflow-report-editor" :value="input" @input="update"> </textarea>
</template>

<script>
import _ from "underscore";

export default {
    props: {
        initialMarkdown: {
            required: true,
            type: String
        },
        onupdate: {
            type: Function
        }
    },
    data: function() {
        return {
            input: this.initialMarkdown
        };
    },
    methods: {
        update: _.debounce(function(e) {
            this.input = e.target.value;
            if (this.onupdate) {
                this.onupdate(this.input);
            }
        }, 300)
    }
};
</script>

<style>
.markdown-textarea {
    border: none;
    border-right: 1px solid #ccc;
    border-left: 1px solid #ccc;
    resize: none;
    outline: none;
    background-color: #f6f6f6;
    font-size: 14px;
    font-family: "Monaco", courier, monospace;
    padding: 20px;

    width: 100%;
    height: 95%; /* what now? this is needed or the editor overtakes workflow toolbar when too much text is added */
}
</style>
