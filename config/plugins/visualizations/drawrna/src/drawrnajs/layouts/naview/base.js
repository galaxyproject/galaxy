var Region = require("./region");

var Base = module.exports = function(){
	this.mate = null;
	this.x = null;
    this.y = null;
	this.extracted = null;
	this.region = new Region();
}

Base.prototype.getMate = function(){
	return this.mate;
}

Base.prototype.setMate = function(mate){
	this.mate = mate;
}

Base.prototype.getX = function(){
	return this.x;
}

Base.prototype.setX = function(x){
	this.x = x;
}

Base.prototype.getY = function(){
	return this.y;
}

Base.prototype.setY = function(y){
	this.y = y;
}

Base.prototype.isExtracted = function(){
	return this.extracted;
}

Base.prototype.setExtracted = function(extracted){
	this.extracted = extracted;
}

Base.prototype.getRegion = function(){
	return this.region;
}

Base.prototype.setRegion = function(region){
	this.region = region;
}
