<template>
    <div id="provenance">
        <div v-show="bco">
            <h2 class="domain">Provenance Domain</h2>
            <tr>
                <td>Name</td>
                <td>{{ bco.provenance_domain.name }}</td>
                <td><button>Edit</button></td>
            </tr>
            <tr>
                <td>Version</td>
                <td>{{ bco.provenance_domain.version }}</td>
                <td><button>Edit</button></td>
            </tr>
            <tr v-for="object in bco.provenance_domain.review" :key="object">
                <td>Review</td>
                <td>
                    Status: {{ object.status }} Date: {{ object.date }}</br>
                    Comment: {{ object.reviewer_comment }}</br>
                    Name: {{ object.reviewer.name }} </br>
                    Affiliation: {{ object.reviewer.affiliation }} </br>
                    Email: {{ object.reviewer.email }} </br>
                </td>
                <td><button>Add</button><br /><button>Remove</button></td>
            </tr>
            <!-- <tr>
                <td>Obsolete</td>
                <td>{{ bco.provenance_domain.obsolete_after }}</td>
                <td><button>Edit</button></td>
            </tr>
            <tr>
                <td>Embargo</td>
                <td v-if="bco.provenance_domain.embargo.start_time !== 'undefined'" >
                    {{ bco.provenance_domain.embargo.start_time }}<br />{{ bco.provenance_domain.embargo.end_time }}
                </td>
            </tr> -->
            <tr>
                <td>Created:</td>
                <td>{{ bco.provenance_domain.created }}</td>
            </tr>
            <tr>
                <td>Modified</td>
                <td>{{ bco.provenance_domain.modified }}</td>
            </tr>
            <tr>
                <td>Contributors</td>
                <td>{{ bco.provenance_domain.contributors }}</td>
                <td><button>Add</button></td>
            </tr>
            <tr>
                <td>License</td>
                <td>{{ bco.provenance_domain.license }}</td>
                <td><button>Edit</button></td>
            </tr>
        </div>
    </div>
</template>

<script>
export default {
    name: "provenance",
    props: ["bco"],
};
</script>
