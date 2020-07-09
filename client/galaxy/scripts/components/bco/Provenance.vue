<template>
    <table>
        <tr>
            <td>Name</td>
            <td>{{ item.name }}</td>
        </tr>
        <tr>
            <td>Version</td>
            <td>{{ item.version }}</td>
        </tr>
        <tr>
            <td>Review</td>
        </tr>
        <tr>
            <td>Status</td>
            <td>Date</td>
            <td>Name</td>
            <td>Email</td>
            <td>Affiliation</td>
            <td>Comment</td>
            <td></td>
        </tr>
        <tr v-for="object in item.review" :key="object">
            <td><textarea>{{ object.status }}</textarea></td>
            <td><textarea>{{ object.date }}</textarea></td>
            <td><textarea>{{ object.reviewer.name }}</textarea></td>
            <td><textarea>{{ object.reviewer.email }}</textarea></td>
            <td><textarea>{{ object.reviewer.affiliation }}</textarea></td>
            <td><textarea>{{ object.reviewer_comment }}</textarea></td>
            <td><button>Remove</button></td>
        </tr>
        <tr>
        <td colspan=6>
        <button>Add Review Step</button>
        </td>
        </tr>
        <tr>
            <td>Obsolete After</td>
            <td>{{ check_key('obsolete_after') }}</td>
        </tr>
        <tr>
            <td>Embargo</td>
            <td>
                {{ check_key('embargo.start_time') }}<br />{{ check_key('embargo.end_time') }}
            </td>
        </tr>
        <tr>
            <td>Created:</td>
            <td>{{ item.created }}</td>
        </tr>
        <tr>
            <td>Modified</td>
            <td>{{ item.modified }}</td>
        </tr>
        <tr>
            <td>Contributors</td>
        </tr>
        <tr>
            <td>Name</td>
            <td>Affiliation</td>
            <td>Email</td>
            <td>Contribution</td>
            <td></td>
        </tr>
        <tr v-for="contrib in item.contributors" :key="contrib.name">
            <td>{{ contrib.name }}</td>
            <td>{{ contrib.affiliation }}</td>
            <td>{{ contrib.email }}</td>
            <td>{{ contrib.contribution[0] }}</td>
        </tr>
        <tr>
        <td colspan=4>
        <button>Add Contributor</button>
        </td>
        </tr>
        <tr>
            <td>License</td>
            <td>{{ item.license }}</td>
        </tr>
    </table>
</template>

<script>
export default {

    methods: {

        check_key: function(incoming) {

            // Check if a key exists.  If not, return 'undefined'.
            var kickback = '';

            if (this.item.hasOwnProperty(incoming)) {

                kickback = this.item[incoming];
            
            } else {

                kickback = 'undefined';

            }

            // Kick it back.
            return kickback;

        }

    },
    name: 'provenance',
    props: {
        item: Object
    }

};
</script>
