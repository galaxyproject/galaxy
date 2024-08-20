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

function addRulePrependInternalRouteToInternalLinks(engine: MarkdownIt, internalRoute: string) {
    const defaultRender =
        engine.renderer.rules.link_open ||
        function (tokens, idx, options, _env, self) {
            return self.renderToken(tokens, idx, options);
        };

    engine.renderer.rules.link_open = function (tokens, idx, options, env, self) {
        const token = tokens[idx];

        if (token) {
            const hrefIndex = token.attrIndex("href");

            if (hrefIndex >= 0) {
                const href = token.attrs![hrefIndex]![1];
                if (href.startsWith("/")) {
                    token.attrs![hrefIndex]![1] = `${internalRoute}${href}`;
                }
            }
        }

        return defaultRender(tokens, idx, options, env, self);
    };
}

function addRuleRemoveBeforeFirstH1(engine: MarkdownIt) {
    const defaultRender = engine.renderer.render;

    engine.renderer.render = function (tokens, options, env) {
        let firstH1Index = tokens.findIndex((token) => token.type === "heading_open" && token.tag === "h1");

        if (firstH1Index !== -1) {
            // If there's a closing tag for the h1, we need to keep it
            if (tokens[firstH1Index + 1]?.type === "heading_close") {
                firstH1Index++;
            }
            tokens = tokens.slice(firstH1Index);
        }

        return defaultRender.call(this, tokens, options, env);
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

/** Appends a horizontal rule to the end of each `<details>` element. */
function appendHrRuleToDetails(doc: Document) {
    const details = doc.querySelectorAll("details");
    details.forEach((detail) => {
        // also, put a <hr class="w-100" /> inside, at the end of each open details tag
        const hr = doc.createElement("hr");
        hr.classList.add("w-100");
        detail.appendChild(hr);
    });
}

/** Replaces `<code>` elements with <i> elements for font-awesome icons. */
function replaceCodesWithIcons(doc: Document) {
    const codes = doc.querySelectorAll("code");
    codes.forEach((code) => {
        const codeContent = code.innerHTML;
        const iconRegex = /^fa-[a-z-]+$/;
        if (iconRegex.test(codeContent)) {
            const icon = document.createElement("i");
            icon.classList.add("fas", codeContent);
            code.replaceWith(icon);
        }
    });
}

/**
 * Adjusts the markdown output based on the options that do not have rules in
 * `engine.renderer.rules`.
 */
function adjustMdForOptions(markdown: string, options: UseMarkdownOptions) {
    if (!options.appendHrRuleToDetails && !options.replaceCodeWithIcon) {
        return markdown;
    }

    const parser = new DOMParser();
    const doc = parser.parseFromString(markdown, "text/html");
    if (options.appendHrRuleToDetails) {
        appendHrRuleToDetails(doc);
    }
    if (options.replaceCodeWithIcon) {
        replaceCodesWithIcons(doc);
    }
    const serializer = new XMLSerializer();
    const modifiedMarkdownOutput = serializer.serializeToString(doc);
    return modifiedMarkdownOutput;
}

interface UseMarkdownOptions {
    openLinksInNewPage?: boolean;
    increaseHeadingLevelBy?: number;
    removeContentBeforeFirstH1?: boolean;
    html?: boolean;
    appendHrRuleToDetails?: boolean;
    replaceCodeWithIcon?: boolean;
    internalRoute?: string;
}

type RawMarkdown = string;
type HTMLString = string;

/** Composable for rendering Markdown strings.  */
export function useMarkdown(options: UseMarkdownOptions = {}) {
    const mdEngine = MarkdownIt({ html: options.html });

    if (options.openLinksInNewPage) {
        addRuleOpenLinksInNewPage(mdEngine);
    }

    if (options.removeContentBeforeFirstH1) {
        addRuleRemoveBeforeFirstH1(mdEngine);
    }

    if (options.internalRoute) {
        addRulePrependInternalRouteToInternalLinks(mdEngine, options.internalRoute);
    }

    if (options.increaseHeadingLevelBy) {
        addRuleHeadingIncreaseLevel(mdEngine, options.increaseHeadingLevelBy);
    }

    function renderMarkdown(markdown: RawMarkdown): HTMLString {
        let renderedMarkdown = mdEngine.render(markdown);
        renderedMarkdown = adjustMdForOptions(renderedMarkdown, options);
        return renderedMarkdown;
    }

    return {
        /** Render markdown string into html. */
        renderMarkdown,
        /** The full Markdown parser/renderer engine for advanced use cases. */
        markdownEngine: readonly(mdEngine),
    };
}
