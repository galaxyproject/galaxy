import MarkdownIt from "markdown-it";

export default {
    methods: {
        adminMarkup(markup) {
            let markupHtml;
            if (markup) {
                markupHtml = MarkdownIt({ html: true }).render(markup);
            } else {
                markupHtml = null;
            }
            return markupHtml;
        },
    },
};
