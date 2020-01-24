<template>
    <b-card>
        <template v-slot:header>
            <h4 class="mb-0">
                References
            </h4>
        </template>
        <table>
            <tr v-for="(xref, index) in xrefs" v-bind:key="index">
                <th>- {{ xref.reftype }}:</th>
                <td>
                    <template v-if="xref.reftype == 'bio.tools'">
                        <a :href="`https://bio.tools/${xref.value}`" target="_blank">{{ xref.value }}</a>
                    </template>
                    <template v-else>
                        {{ xref.value }}
                    </template>
                </td>
            </tr>
        </table>
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
                this.xrefs = response.data;
            })
            .catch(e => {
                console.error(e);
            });
    }
};
</script>
