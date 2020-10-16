importScripts('sql.js');

onmessage = function(message){

    http(message.data.url,message.data.sql);

    function http(url, sql)
    {
        var url = url;
        var sql = sql;

        var xhr = new XMLHttpRequest();
        xhr.open('GET', url, true);
        xhr.responseType = 'arraybuffer';

        xhr.onload = function(e) {
          postMessage(applyTransform(this.response, sql));
          close();
        };

        xhr.send();
    }

    function applyTransform(result, sql)
    {
        var data = [];
        var uInt8Array = new Uint8Array(result);
        var db = new SQL.Database(uInt8Array);
        var stmt = db.prepare(sql);
        while(stmt.step())
        {
            data.push(stmt.getAsObject())
        }
        db.close();
        return data;
    }
}
