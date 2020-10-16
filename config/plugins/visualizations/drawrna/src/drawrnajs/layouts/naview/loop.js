var Loop = module.exports = function(){
	this.nconnection = null;
	this.connections = [];
	this._connections = [];
	this.number = null;
	this.depth = null;
	this.mark = null;
	this.x = null;
    this.y = null;
    this.radius = null;
}

Loop.prototype.getNconnection = function() {
	return this.nconnection;
}

Loop.prototype.setNconnection = function(nconnection) {
	this.nconnection = nconnection;
}

Loop.prototype.setConnection = function(i, c){
	var Connection = require("./connection");
	if (c != null){
		this._connections[i] = c;
    }
	else {
		if (!this._connections[i]){
			this._connections[i] = new Connection();
		}
		this._connections[i].setNull(true);
	}
}

Loop.prototype.getConnection = function(i){
	var Connection = require("./connection");
	if (!this._connections[i]){
        this._connections[i] = new Connection();
    }
	var c = this._connections[i];
	if (c.isNull()){
		return null;
    }
	else {
		return c;
    }
}

Loop.prototype.addConnection = function(i, c){
	this._connections.push(c);
}

Loop.prototype.getNumber = function(){
	return this.number;
}

Loop.prototype.setNumber = function(number){
	this.number = number;
}

Loop.prototype.getDepth = function(){
	return this.depth;
}

Loop.prototype.setDepth = function(depth){
	this.depth = depth;
}

Loop.prototype.isMark = function(){
	return this.mark;
}

Loop.prototype.setMark = function(mark){
	this.mark = mark;
}

Loop.prototype.getX = function(){
	return this.x;
}

Loop.prototype.setX = function(x){
	this.x = x;
}

Loop.prototype.getY = function(){
	return this.y;
}

Loop.prototype.setY = function(y){
	this.y = y;
}

Loop.prototype.getRadius = function(){
	return this.radius;
}

Loop.prototype.setRadius = function(radius){
	this.radius = radius;
}
