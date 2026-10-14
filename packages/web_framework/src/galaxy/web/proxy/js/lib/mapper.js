var fs = require('fs');
var sqlite3 = require('sqlite3')
var watch = require('node-watch');


var endsWith = function(subjectString, searchString) {
    var position = subjectString.length;
    position -= searchString.length;
    var lastIndex = subjectString.indexOf(searchString, position);
    return lastIndex !== -1 && lastIndex === position;
};


var updateFromJson = function(path, map) {
    var content = fs.readFileSync(path, 'utf8');
    var keyToSession = JSON.parse(content);
    var newSessions = {};
    for(var key in keyToSession) {
        newSessions[key] = {'target': {'host': keyToSession[key]['host'], 'port': parseInt(keyToSession[key]['port'])}};
    }
    for(var oldSession in map) {
        if(!(oldSession in newSessions)) {
            delete map[ oldSession ];
        }
    }
    for(var newSession in newSessions) {
        map[newSession] = newSessions[newSession];
    }
}

var updateFromSqlite = function(path, map) {
    var newSessions = {};
    var loadSessions = function() {
        db.each("SELECT key, host, port FROM gxproxy2", function(err, row) {
            var key = row['key'];
            var target = {'host': row['host'], 'port': parseInt(row['port'])};
            newSessions[key] = {'target': target};
        }, finish);
    };

    var finish = function() {
        for(var oldSession in map) {
            if(!(oldSession in newSessions)) {
                delete map[ oldSession ];
            }
        }
        for(var newSession in newSessions) {
            map[newSession] = newSessions[newSession];
        }
        db.close();
    };

    var db = new sqlite3.Database(path, loadSessions);
};


var mapFor = function(path) {
    var map = {};
    var loadMap;
    if(endsWith(path, '.sqlite')) {
        loadMap = function() {
            updateFromSqlite(path, map);
        }
    } else {
        loadMap = function() {
            updateFromJson(path, map);
        }
    }
    console.log("Watching path " + path);
    loadMap();
    watch(path, loadMap);
    return map;
};

exports.mapFor = mapFor;
