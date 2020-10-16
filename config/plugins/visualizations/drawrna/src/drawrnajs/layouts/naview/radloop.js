var Radloop = module.exports = function(){
	this.radius = null;
	this.loopnumber = null;
	this.next = null;
    this.prev = null;
}

Radloop.prototype.getRadius = function(){
	return this.radius;
}

Radloop.prototype.setRadius = function(radius){
	this.radius = radius;
}

Radloop.prototype.getLoopnumber = function(){
	return this.loopnumber;
}

Radloop.prototype.setLoopnumber = function(loopnumber){
	this.loopnumber = loopnumber;
}

Radloop.prototype.getNext = function(){
	return this.next;
}

Radloop.prototype.setNext = function(next){
	this.next = next;
}

Radloop.prototype.getPrev = function(){
	return this.prev;
}

Radloop.prototype.setPrev = function(prev){
	this.prev = prev;
}
