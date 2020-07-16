// Description:  For converting JSON field names into readable field names.

export default {

    // Parse the names.
    parse_names: function(incoming) {

        // Is incoming a string?
        if (typeof(incoming) === 'string') {

        // Does the name match the dash pattern?
        if (incoming.search("((.*?)_)*") != -1) {

            // Found a match, so split and capitalize.
            var split_up = incoming.split('_');
            
            // Source:  https://stackoverflow.com/questions/1026069/how-do-i-make-the-first-letter-of-a-string-uppercase-in-javascript

            var new_array = split_up.map(function(e) {
                return e.charAt(0).toUpperCase() + e.slice(1);
            });
            
            // Re-join.
            incoming = new_array.join(' ');

        }

        }
        
        return (incoming)

    }

}
