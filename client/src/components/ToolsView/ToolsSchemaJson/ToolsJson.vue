<template>
    <div />
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

export default {
    data() {
        return { schemaTagObj: {} };
    },
    created() {
        axios
            .get(`${getAppRoot()}api/tools?tool_help=True`)
            .then((response) => {
                this.schemaTagObj = this.createToolsJson(response.data);
                const el = document.createElement("script");
                el.id = "schema-json";
                el.type = "application/ld+json";
                el.text = JSON.stringify(this.schemaTagObj);
                document.head.appendChild(el);
            })
            .catch((error) => {
                console.error(error);
            });
    },
    methods: {
        createToolsJson(tools) {
            function extractSections(acc, section) {
                function extractTools(_acc, tool) {
                    return tool.name
                        ? [
                              ..._acc,
                              {
                                  "@type": "SoftwareApplication",
                                  operatingSystem: "Any",
                                  applicationCategory: "Web application",
                                  name: tool.name,
                                  description: tool.help || tool.description,
                                  softwareVersion: tool.version,
                                  url: getAppRoot() + String(tool.link).substring(1),
                              },
                          ]
                        : _acc;
                }
                if ("elems" in section) {
                    return acc.concat(section.elems.reduce(extractTools, []));
                } else {
                    return acc;
                }
            }
            return {
                "@context": "http://schema.org",
                "@graph": tools.reduce(extractSections, []),
            };
        },
    },
};
</script>
