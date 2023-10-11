import MarkdownIt from "markdown-it";
import { readonly } from "vue";

const mdEngine = MarkdownIt();

/**
 * Adds a rule to open all links in a new page.
 * https://github.com/markdown-it/markdown-it/blob/master/docs/architecture.md#renderer
 */
function addRuleOpenLinksInNewPage(engine) {
    var defaultRender =
        engine.renderer.rules.link_open ||
        function (tokens, idx, options, env, self) {
            return self.renderToken(tokens, idx, options);
        };
    engine.renderer.rules.link_open = function (tokens, idx, options, env, self) {
        var aIndex = tokens[idx].attrIndex("target");
        if (aIndex < 0) {
            tokens[idx].attrPush(["target", "_blank"]);
        } else {
            tokens[idx].attrs[aIndex][1] = "_blank";
        }
        return defaultRender(tokens, idx, options, env, self);
    };
}

/** Composable for rendering Markdown strings.  */
export function useMarkdown(options = {}) {
    if (options.openLinksInNewPage) {
        addRuleOpenLinksInNewPage(mdEngine);
    }

    function renderMarkdown(markdown) {
        return mdEngine.render(markdown);
    }

    return {
        /** Render markdown string into html. */
        renderMarkdown,
        /** The full Markdown parser/renderer engine for advanced use cases. */
        markdownEngine: readonly(mdEngine),
    };
}
