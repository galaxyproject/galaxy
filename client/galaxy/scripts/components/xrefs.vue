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
        reftype: {
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
                this.reftype = "";
                this.content = "<table>";
                for (var raw_xref of response.data) {
                    try {
                        this.reftype = raw_xref.reftype;
                        this.content += "<tr>";
                        this.content += "<th> - ";
                        this.content += this.reftype;
                        this.content += "</th>";
                        this.content += "<td> : ";
                        if (this.reftype == "bio.tools") {
                            this.content += "<a href=\"https://bio.tools/" + raw_xref.value + "\" target=\"_blank\">" + raw_xref.value + "</a>";
                        }
                        else {
                            this.content += raw_xref.value;
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
