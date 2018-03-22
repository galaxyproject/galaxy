const fs = require("fs");

fs.createReadStream("test.log").pipe(fs.createWriteStream("newLog.log"));

// Read the directory
fs.readdir(dir, function(err, list) {
    // Return the error if something went wrong
    if (err) return action(err);

    // For every file in the list
    list.forEach(function(file) {
        // Full path of that file
        path = dir + "/" + file;
        // Get the file's stats
        fs.stat(path, function(err, stat) {
            console.log(stat);
            // If the file is a directory
            if (stat && stat.isDirectory())
                // Dive into the directory
                dive(path, action);
            else
                // Call the action
                action(null, path);
        });
    });
});
