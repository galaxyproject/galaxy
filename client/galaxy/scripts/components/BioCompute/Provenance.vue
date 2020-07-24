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
            <td><textarea :data-jpath="`provenance_domain.review[${index}].status`" v-on:input='event => check_input(event)' v-model="object.status"/></td>
            <td><textarea v-on:input='event => check_input(event)' v-model="object.date"/></textarea></td>
            <td><textarea v-on:input='event => check_input(event)' v-model="object.reviewer.name"/></textarea></td>
            <td><textarea v-on:input='event => check_input(event)'  v-model="object.reviewer.email" /></textarea></td>
            <td><textarea v-on:input='event => check_input(event)' v-model="object.reviewer.affiliation"/></textarea></td>
            <td><textarea v-on:input='event => check_input(event)' v-model="object.reviewer_comment"/></textarea></td>
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

            if (Object.prototype.hasOwnProperty(this.item, incoming)) {

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

            console.log('value')
            console.log(value);

            // Where is it going in the original JSON?
            var json_path = incoming.target.dataset.jpath;

            console.log('json_path');
            console.log(json_path);

            // Set the user-editable ID.
            var user_invoke_id = this.$props.invokeId + '-USER';

            // Retrieve the store, converted to JSON.
            var stored = JSON.parse(sessionStorage.getItem(user_invoke_id));

            console.log('STORED BEFORE');
            console.log(stored);

            // Create the key tree (more secure than straight
            // eval statements).
            var key_tree = json_path.split('.');

            console.log('KEY TREE');
            console.log(key_tree);

            // Each part of the key tree must either be 1) a 
            // valid key in our stored object, or 2) a string
            // of the exact form [digit].

            // Create a flag to indicate a valid string,
            // assuming outright that the string is valid.
            var valid_string = true;

            // Check each part.
            /*
            for(var i = 0; i < key_tree.length; i++) {
                console.log(key_tree[i]);

                // Source:  https://stackoverflow.com/questions/20804163/check-if-a-key-exists-inside-a-json-object

                if (Object.prototype.hasOwnProperty.call(stored, key_tree[i])) {
                    console.log('HAS KEY');
                    // Dummy block
            
                } else if (/^\[\d+\]$/.test(key_tree[i])) {
                    console.log('HAS ARRAY');
                    // Source:  https://stackoverflow.com/questions/6603015/check-whether-a-string-matches-a-regex-in-js

                    // Dummy block

                } else {
                    console.log('FAILED');
                    // Something failed.
                    valid_string = false;

                }

            }
            */
            // If everything was valid, go ahead and evaluate.
            if(valid_string === true) {

                console.log('HERE');
                // Evaluate (execute literal statement).
                console.log('stored.' + json_path + ' = \'' + value + '\'');

                // Set the object value according to the JSON path.
                eval('stored.' + json_path + ' = \'' + value + '\'');

                // Re-set the session object.
                sessionStorage.setItem(user_invoke_id, JSON.stringify(stored));

            }            

            console.log('STORED AFTER');
            console.log(stored);
        }

    },
    name: 'provenance',
    props: {
        item: Object,
        invokeId: String
    }

};
</script>
