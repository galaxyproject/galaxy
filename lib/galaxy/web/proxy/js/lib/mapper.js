var fs = require('fs');


var mapFor = function(path) {
	var map = {};

	var loadMap = function() {
 		var content = fs.readFileSync(path, 'utf8');
 		var keyToSession = JSON.parse(content);
 		var newSessions = {};
 		for(var key in keyToSession) {
 			var hostAndPort = key.split(":");
 			// 'host': hostAndPort[0],
 			newSessions[keyToSession[key]] = {'target': {'host': hostAndPort[0], 'port': parseInt(hostAndPort[1])}};
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

	console.log("Watching path " + path);
	loadMap();
	fs.watch(path, loadMap);

	return map;
}

exports.mapFor = mapFor;