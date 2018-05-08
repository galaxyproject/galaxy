var Loop = require("./loop");
var Region = require("./region");

var Connection = module.exports = function(){
	this.loop = new Loop();
	this.region = new Region();
	// Start and end form the 1st base pair of the region.
	this.start = null;
    this.end = null;
	this.xrad = null;
    this.yrad = null;
    this.angle = null;
	// True if segment between this connection and the
	// next must be extruded out of the circle
	this.extruded = null;
	// True if the extruded segment must be drawn long.
	this.broken = null;

	this._isNull = false;
}

Connection.prototype.isNull = function(){
	return this._isNull;
}

Connection.prototype.setNull = function(isNull){
	this._isNull = isNull;
}

Connection.prototype.getLoop = function(){
	return this.loop;
}

Connection.prototype.setLoop = function(loop) {
	this.loop = loop;
}

Connection.prototype.getRegion = function(){
	return this.region;
}

Connection.prototype.setRegion = function(region){
	this.region = region;
}

Connection.prototype.getStart = function(){
	return this.start;
}

Connection.prototype.setStart = function(start) {
	this.start = start;
}

Connection.prototype.getEnd = function(){
	return this.end;
}

Connection.prototype.setEnd = function(end){
	this.end = end;
}

Connection.prototype.getXrad = function(){
	return this.xrad;
}

Connection.prototype.setXrad = function(xrad){
	this.xrad = xrad;
}

Connection.prototype.getYrad = function(){
	return this.yrad;
}

Connection.prototype.setYrad = function(yrad) {
	this.yrad = yrad;
}

Connection.prototype.getAngle = function(){
	return this.angle;
}

Connection.prototype.setAngle = function(angle){
	this.angle = angle;
}

Connection.prototype.isExtruded = function(){
	return this.extruded;
}

Connection.prototype.setExtruded = function(extruded){
	this.extruded = extruded;
}

Connection.prototype.isBroken = function(){
	return this.broken;
}

Connection.prototype.setBroken = function(broken){
	this.broken = broken;
}
