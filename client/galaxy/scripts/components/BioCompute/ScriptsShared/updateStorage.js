// Description:  The function for storing field values into the session store.

// Source:  https://blog.bitsrc.io/understanding-mixins-in-vue-js-bdcf9e02a7c1

export default {

    methods: {

        store_input: function(incoming) {

            // Source:  https://stackoverflow.com/questions/48779743/trying-to-retrieve-element-data-attribute-from-vue-js-component-in-laravel

            // Arguments

            // incoming: from a template element.

            // What was typed?
            var value = incoming.target.value;

            //console.log('value')
            //console.log(value);

            // Where is it going in the original JSON?
            var json_path = incoming.target.dataset.jpath;

            //console.log('json_path');
            //console.log(json_path);

            // Set the user-editable ID.
            var user_invoke_id = this.$props.invokeId + '-USER';

            // Retrieve the store with this ID, converted to JSON.
            var stored = JSON.parse(sessionStorage.getItem(user_invoke_id));

            //console.log('STORED BEFORE');
            //console.log(stored);

            /* Security - to come later...

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
            //if(valid_string === true) {

                //console.log('HERE');
                // Evaluate (execute literal statement).
                //console.log('stored.' + json_path + ' = \'' + value + '\'');

                // Set the object value according to the JSON path.
                eval('stored.' + json_path + ' = \'' + value + '\'');

                // Re-set the session object.
                sessionStorage.setItem(user_invoke_id, JSON.stringify(stored));

            //}            

            //console.log('STORED AFTER');
            //console.log(stored);
        }

    }

}

