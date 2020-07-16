<template>
    <table>
        <tr>
        <td colspan=3>
            <h2>Provenance Domain</h2>
        </td>
        </tr>
        <tr>
            <td>Name</td>
            <td colspan=2>{{ item.name }}</td>
        </tr>
        <tr>
            <td>Version</td>
            <td>{{ item.version }}</td>
        </tr>
        <tr>
            <td class='border_except'>Review</td>
        </tr>
        <tr>
            <td></td>
            <td>Status</td>
            <td>Date</td>
            <td>Name</td>
            <td>Email</td>
            <td>Affiliation</td>
            <td>Comment</td>
            <td></td>
        </tr>
        <tr v-for="(object, index) in item.review" :key="object">
            <td></td>
            <!-- Source:  https://stackoverflow.com/questions/51953173/how-do-i-pass-input-text-using-v-onchange-to-my-vue-method -->
            <td><textarea :data-jpath="`bco_object.provenance_domain.review.[${index}].status`" v-on:input='event => check_input(event)'>{{ object.status }}</textarea></td>
            <td><textarea v-on:input='event => check_input(event)'>{{ object.date }}</textarea></td>
            <td><textarea v-on:input='event => check_input(event)'>{{ object.reviewer.name }}</textarea></td>
            <td><textarea v-on:input='event => check_input(event)'>{{ object.reviewer.email }}</textarea></td>
            <td><textarea v-on:input='event => check_input(event)'>{{ object.reviewer.affiliation }}</textarea></td>
            <td><textarea v-on:input='event => check_input(event)'>{{ object.reviewer_comment }}</textarea></td>
            <td><button>Remove</button></td>
        </tr>
        <tr>
        <td></td>
        <td colspan=6>
        <button>Add Review Step</button>
        </td>
        <tr>
            <td colspan=8>
            </td>
        </tr>
        </tr>
        <tr>
            <td>Obsolete After</td>
            <td>{{ check_key('obsolete_after') }}</td>
        </tr>
        <tr>
            <td colspan=8>
            </td>
        </tr>
        <tr>
            <td>Embargo</td>
            <td colspan=2></td>
            <td class='bold_contain'>Created</td>
            <td></td>
            <td class='bold_contain'>Modified</td>
        </tr>
        <tr>
            <td class='bold_except'>
                {{ check_key('embargo.start_time') }}
            </td>
            <td>
                {{ check_key('embargo.end_time') }}
            </td>
            <td></td>
            <td>{{ item.created }}</td>
            <td></td>
            <td>{{ item.modified }}</td>
        </tr>
        <tr>
            <td colspan=8>
            </td>
        </tr>
        <tr>
            <td>Contributors</td>
        </tr>
        <tr>
            <td>Name</td>
            <td class='bold_contain'>Affiliation</td>
            <td class='bold_contain'>Email</td>
            <td class='bold_contain'>Contribution</td>
            <td></td>
        </tr>
        <tr v-for="contrib in item.contributors" :key="contrib.name">
            <td class='bold_except'>{{ contrib.name }}</td>
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

        },

        check_input: function(incoming) {

            // Source:  https://stackoverflow.com/questions/48779743/trying-to-retrieve-element-data-attribute-from-vue-js-component-in-laravel

            // What was typed?
            var value = incoming.target.value;

            // Where is it going in the original JSON?
            var json_path = incoming.target.dataset.jpath;

            console.log(value);
            console.log(json_path);

        }

    },
    name: 'provenance',
    props: {
        item: Object
    }

};
</script>
