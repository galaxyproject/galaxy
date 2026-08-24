import "highlight.js/styles/github.css";

import hljs from "highlight.js/lib/core";
import bash from "highlight.js/lib/languages/bash";
import json from "highlight.js/lib/languages/json";
import yaml from "highlight.js/lib/languages/yaml";

hljs.registerLanguage("bash", bash);
hljs.registerLanguage("console", bash);
hljs.registerLanguage("json", json);
hljs.registerLanguage("yaml", yaml);

const SUPPORTED_LANGUAGES = new Set(["bash", "console", "json", "yaml"]);

export function highlightAuthoringCode(code: string, language: string): string {
    if (!SUPPORTED_LANGUAGES.has(language)) {
        return "";
    }
    const highlightedCode = hljs.highlight(code, { language, ignoreIllegals: true }).value;
    return `<pre><code class="hljs language-${language}">${highlightedCode}</code></pre>`;
}
