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
    this.debug = options.verbose;
    this.reverseProxy = options.reverseProxy;
    this.port = options.port;

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
    if(request.url.indexOf('rstudio') != -1){
        var remap = {
            'content-type': 'Content-Type',
            'content-length': 'Content-Length',
        }
        // RStudio isn't spec compliant and pitches a fit on NodeJS's http module's lowercase HTTP headers
        for(var i = 0; i<Object.keys(remap).length; i++){
            var key = Object.keys(remap)[i];
            if(key in request.headers){
                request.headers[remap[key]] = request.headers[key];
                delete request.headers[key];
            }
        }
        if('Content-Type' in request.headers && request.headers['Content-Type'] == 'application/x-www-form-urlencoded; charset=UTF-8'){
            request.headers['Content-Type'] = 'application/x-www-form-urlencoded';
        }
    }
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
    var othis = this;
    var target = this.targetForRequest(req);
    if(this.debug) {
        console.log("PROXY " + req.method + " " + req.url + " to " + target.host + ':' + target.port);
    }
    var origin = req.headers.origin;
    this.rewriteRequest(req);
    res.oldWriteHead = res.writeHead;

    res.writeHead = function(statusCode, headers) {
        if(othis.reverseProxy && statusCode === 302){
            if(res && res._headers){
                if(othis.debug){
                    console.log("Original Location Header: " + res._headers.location);
                }
                if(res._headers.location){
                    res._headers.location = res._headers.location.replace('http://localhost/', 'http://localhost:' + othis.port + '/');
                }
                if(othis.debug){
                    console.log("Rewritten Location Header: " + res._headers.location);
                }
            }
        }
        try {
            if(origin){
                res.setHeader('Access-Control-Allow-Origin', origin);
            }
            res.setHeader('Access-Control-Allow-Credentials', 'true');

            if(!headers){
                headers = {};
            }
            res.oldWriteHead(statusCode, headers);
        }
        catch (error) {
          console.log("Header could not be modified.");
          console.log(error);
        }

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
    if(this.debug) {
        console.log("PROXY WS " + req.url + " to " + target.host + ':' + target.port);
    }
    var origin = req.headers.origin;
    this.rewriteRequest(req);
    res.oldWriteHead = res.writeHead;
    res.writeHead = function(statusCode, headers) {
        try {
            if(origin){
                res.setHeader('Access-Control-Allow-Origin', origin);
            }
            res.setHeader('Access-Control-Allow-Credentials', 'true');
            if(!headers){ headers = {}; }
            res.oldWriteHead(statusCode, headers);
        }
        catch (error) {
          console.log("Header could not be modified.");
          console.log(error);
        }
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
