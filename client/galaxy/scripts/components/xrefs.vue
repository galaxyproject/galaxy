<template>
    <b-card>
        <h4 slot="header" class="mb-0">
            References
        </h4>
        <span v-html="content"></span>
    </b-card>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

export default {
    props: {
        source: {
            type: String,
            required: true
        },
        id: {
            type: String,
            required: true
        },
        type: {
            type: String,
            required: true
        },
        content: {
            type: String,
            required: true
        },
        viewRender: {
            type: Boolean,
            requried: false,
            default: true
        }
    },
    data() {
        return {
            xrefs: [],
            errors: []
        };
    },
    created: function() {
        axios
            .get(`${getAppRoot()}api/${this.source}/${this.id}/xrefs`)
            .then(response => {
                this.type = "";
                this.content = "<table>";
                for (var raw_xref of response.data) {
                    try {
                        this.type = raw_xref.reftype;
                        this.content += "<tr>";
                        this.content += "<th> - ";
                        this.content += this.type;
                        this.content += "</th>";
                        this.content += "<td> : ";
                        if (this.type == "bio.tools") {
                            this.content += "<a href=\"https://bio.tools/" + raw_xref.content + "\" target=\"_blank\">" + raw_xref.content + "</a>";
                        }
                        else {
                            this.content += raw_xref.content;
                        }
                        this.content += "</td>";
                        this.content += "</tr>";
                    } catch (err) {
                        console.warn("Error parsing xref: " + err);
                    }
                }
                this.content += "</table>";
            })
            .catch(e => {
                console.error(e);
            });
    }
};
</script>
