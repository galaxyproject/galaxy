import MarkdownIt from "markdown-it";
import type Token from "markdown-it/lib/token";
import { readonly } from "vue";

/**
 * Adds a rule to open all links in a new page.
 * https://github.com/markdown-it/markdown-it/blob/master/docs/architecture.md#renderer
 */
function addRuleOpenLinksInNewPage(engine: MarkdownIt) {
    const defaultRender =
        engine.renderer.rules.link_open ||
        function (tokens, idx, options, _env, self) {
            return self.renderToken(tokens, idx, options);
        };

    engine.renderer.rules.link_open = function (tokens, idx, options, env, self) {
        const token = tokens[idx];

        if (token) {
            const aIndex = token.attrIndex("target");

            if (aIndex && aIndex < 0) {
                token.attrPush(["target", "_blank"]);
            } else {
                token.attrs![aIndex]![1] = "_blank";
            }
        }

        return defaultRender(tokens, idx, options, env, self);
    };
}

function addRuleHeadingIncreaseLevel(engine: MarkdownIt, increaseBy: number) {
    const defaultOpen =
        engine.renderer.rules.heading_open ||
        function (tokens, idx, options, _env, self) {
            return self.renderToken(tokens, idx, options);
        };

    const defaultClose =
        engine.renderer.rules.heading_close ||
        function (tokens, idx, options, _env, self) {
            return self.renderToken(tokens, idx, options);
        };

    const increaseHeadingLevel = (token: Token) => {
        const level = parseInt(token.tag[1] ?? "1");
        token.tag = `h${level + increaseBy}`;
    };

    engine.renderer.rules.heading_open = function (tokens, idx, options, env, self) {
        const token = tokens[idx];

        if (token) {
            increaseHeadingLevel(token);
        }

        return defaultOpen(tokens, idx, options, env, self);
    };

    engine.renderer.rules.heading_close = function (tokens, idx, options, env, self) {
        const token = tokens[idx];

        if (token) {
            increaseHeadingLevel(token);
        }

        return defaultClose(tokens, idx, options, env, self);
    };
}

interface UseMarkdownOptions {
    openLinksInNewPage?: boolean;
    increaseHeadingLevelBy?: number;
}

type RawMarkdown = string;
type HTMLString = string;

/** Composable for rendering Markdown strings.  */
export function useMarkdown(options: UseMarkdownOptions = {}) {
    const mdEngine = MarkdownIt();

    if (options.openLinksInNewPage) {
        addRuleOpenLinksInNewPage(mdEngine);
    }

    if (options.increaseHeadingLevelBy) {
        addRuleHeadingIncreaseLevel(mdEngine, options.increaseHeadingLevelBy);
    }

    function renderMarkdown(markdown: RawMarkdown): HTMLString {
        return mdEngine.render(markdown);
    }

    return {
        /** Render markdown string into html. */
        renderMarkdown,
        /** The full Markdown parser/renderer engine for advanced use cases. */
        markdownEngine: readonly(mdEngine),
    };
}
