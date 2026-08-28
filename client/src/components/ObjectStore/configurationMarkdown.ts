import MarkdownIt from "markdown-it";

type SyntaxHighlighter = NonNullable<MarkdownIt.Options["highlight"]>;

export function markup(markup: string, adminConfigured: boolean, syntaxHighlighter?: SyntaxHighlighter): string | null {
    let markupHtml;
    const allowHtml = adminConfigured ? true : false;
    if (markup) {
        markupHtml = MarkdownIt({ html: allowHtml, highlight: syntaxHighlighter }).render(markup);
    } else {
        markupHtml = null;
    }
    return markupHtml;
}
