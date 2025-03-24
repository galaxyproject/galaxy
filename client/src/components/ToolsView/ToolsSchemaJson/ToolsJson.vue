<template>
    <div />
</template>

<script>
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

export default {
    data() {
        return { schemaTagObj: {} };
    },
    async created() {
        let tools = [];
        await axios
            .get(`${getAppRoot()}api/tools?in_panel=False&tool_help=True`)
            .then(({ data }) => {
                tools = data.reduce((acc, item) => {
                    acc[item.id] = item;
                    return acc;
                }, {});
            })
            .catch((error) => {
                console.error("未能加载全部工具列表", error);
            });
        if (Object.keys(tools).length > 0) {
            await axios
                .get(`${getAppRoot()}api/tool_panels/default`)
                .then(({ data }) => {
                    this.schemaTagObj = this.createToolsJson(tools, data);
                    const el = document.createElement("script");
                    el.id = "schema-json";
                    el.type = "application/ld+json";
                    el.text = JSON.stringify(this.schemaTagObj);
                    document.head.appendChild(el);
                })
                .catch((error) => {
                    console.error("未能通过ID加载工具分区", error);
                });
        }
    },
    methods: {
        createToolsJson(tools, panel) {
            const sections = Object.values(panel);
            function extractSections(acc, section) {
                function extractTools(_acc, toolId) {
                    const tool = tools[toolId];
                    return tool && tool.name
                        ? [
                              ..._acc,
                              {
                                  "@type": "SoftwareApplication",
                                  operatingSystem: "任何系统",
                                  applicationCategory: "网页应用程序",
                                  name: tool.name,
                                  description: tool.help || tool.description,
                                  softwareVersion: tool.version,
                                  url: getAppRoot() + String(tool.link).substring(1),
                              },
                          ]
                        : _acc;
                }
                if ("tools" in section) {
                    return acc.concat(section.tools.reduce(extractTools, []));
                } else {
                    return acc;
                }
            }
            return {
                "@context": "http://schema.org",
                "@graph": sections.reduce(extractSections, []),
            };
        },
    },
};
</script>
