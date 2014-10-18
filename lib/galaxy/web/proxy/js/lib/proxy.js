var http = require('http'),
    httpProxy = require('http-proxy');

var bound = function (that, method) {
    // bind a method, to ensure `this=that` when it is called
    // because prototype languages are bad
    return function () {
        method.apply(that, arguments);
    };
};

var DynamicProxy = function(options) {
	var dynamicProxy = this;
	this.sessionCookie = options.sessionCookie;
	this.sessionMap = options.sessionMap;

    var log_errors = function(handler) {
        return function (req, res) {
            try {
                return handler.apply(dynamicProxy, arguments);
            } catch (e) {
                console.log("Error in handler for " + req.method + ' ' + req.url + ': ', e);
            }
        };
    };

    var proxy = this.proxy = httpProxy.createProxyServer({
        ws : true,
    });

    this.proxy_server = http.createServer(
    	log_errors(dynamicProxy.handleProxyRequest)
    );
	this.proxy_server.on('upgrade', bound(this, this.handleWs));
};

DynamicProxy.prototype.rewriteRequest = function(request) {
}

DynamicProxy.prototype.targetForRequest = function(request) {
    // return proxy target for a given url
    var session = this.findSession(request);
    for (var mappedSession in this.sessionMap) {
    	if(session == mappedSession) {
            return this.sessionMap[session].target;
        }
    }

    return null;
};

DynamicProxy.prototype.findSession = function(request) {
    var sessionCookie = this.sessionCookie;
        rc = request.headers.cookie;
    if(!rc) {
        return null;
    }
    var cookies = rc.split(';');
    for(var cookieIndex in cookies) {
    	var cookie = cookies[cookieIndex];
        var parts = cookie.split('=');
		var partName = parts.shift().trim();
        if(partName == sessionCookie) {
        	return unescape(parts.join('='))
        }
    }

    return null;
};

DynamicProxy.prototype.handleProxyRequest = function(req, res) {
    var target = this.targetForRequest(req);
    console.log("PROXY " + req.method + " " + req.url + " to " + target);
    var origin = req.headers.origin;
    this.rewriteRequest(req);
    res.oldWriteHead = res.writeHead;
    res.writeHead = function(statusCode, headers) {
        res.setHeader('Access-Control-Allow-Origin', origin);
        res.setHeader('Access-Control-Allow-Credentials', 'true');
        res.oldWriteHead(statusCode, headers);
    }
    this.proxy.web(req, res, {
        target: target
    }, function (e) {
        console.log("Proxy error: ", e);
        res.writeHead(502);
        res.write("Proxy target missing");
        res.end();
    });
};

DynamicProxy.prototype.handleWs = function(req, res, head) {
    // no local route found, time to proxy
    var target = this.targetForRequest(req);
    console.log("PROXY WS " + req.url + " to " + req.url);
    var origin = req.headers.origin;
    this.rewriteRequest(req);
    res.oldWriteHead = res.writeHead;
    res.writeHead = function(statusCode, headers) {
        res.setHeader('Access-Control-Allow-Origin', origin);
        res.setHeader('Access-Control-Allow-Credentials', 'true');
        res.oldWriteHead(statusCode, headers);
    }
    this.proxy.ws(req, res, head, {
        target: target
    }, function (e) {
        console.log("Proxy error: ", e);
        res.writeHead(502);
        res.write("Proxy target missing");
        res.end();
    });
};

exports.DynamicProxy = DynamicProxy;
