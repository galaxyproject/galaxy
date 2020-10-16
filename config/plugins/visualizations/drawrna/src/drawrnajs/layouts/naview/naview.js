var Loop = require("./loop");
var Base = require("./base");
var Region = require("./region");
var Connection = require("./connection");
var Radloop = require("./radloop");

var NAView = module.exports = function(){
    this.ANUM = 9999.0;
	this.MAXITER = 500;

	this.bases = [];
	this.nbase = null;
    this.nregion = null;
    this.loop_count = null;

	this.root = new Loop();
	this.loops = [];

	this.regions = [];

	this.rlphead = new Radloop();

	this.lencut = 0.8;
	this.RADIUS_REDUCTION_FACTOR = 1.4;

	// show algorithm step by step
	this.angleinc = null;

	this._h = null;

	// private boolean noIterationFailureYet = true;

	this.HELIX_FACTOR = 0.6;
	this.BACKBONE_DISTANCE = 27;
}

NAView.prototype.naview_xy_coordinates = function(pair_table2){
    var x = [];
	var y = [];
    if (pair_table2.length === 0){
        return 0;
    }
    var i;
    var pair_table = [];
    pair_table.push(pair_table2.length);
    for (var j = 0; j < pair_table2.length; j++){
        pair_table.push(pair_table2[j] + 1);
    }
    this.nbase = pair_table[0];
    this.bases = [];
    for (var index = 0; index < this.nbase + 1; index++){
        this.bases.push(new Base());
    }
    this.regions = [];
    for (var index = 0; index < this.nbase + 1; index++){
        this.regions.push(new Region());
    }
    this.read_in_bases(pair_table);
    this.rlphead = null;
    this.find_regions();
    this.loop_count = 0;
    this.loops = [];
    for (var index = 0; index < this.nbase + 1; index++){
        this.loops.push(new Loop());
    }
    this.construct_loop(0);
    this.find_central_loop();
    this.traverse_loop(this.root, null);

    for (i = 0; i < this.nbase; i++){
        x.push(100 + this.BACKBONE_DISTANCE * this.bases[i + 1].getX());
        y.push(100 + this.BACKBONE_DISTANCE * this.bases[i + 1].getY());
    }

    return {
        nbase: this.nbase,
        x: x,
        y: y
    }
}

NAView.prototype.read_in_bases = function read_in_bases(pair_table){
    var i = null;
    var npairs = null;

    // Set up an origin.
    this.bases.push(new Base());
    this.bases[0].setMate(0);
    this.bases[0].setExtracted(false);
    this.bases[0].setX(this.ANUM);
    this.bases[0].setY(this.ANUM);

    for (npairs = 0, i = 1; i <= this.nbase; i++){
        this.bases.push(new Base());
        this.bases[i].setExtracted(false);
        this.bases[i].setX(this.ANUM);
        this.bases[i].setY(this.ANUM);
        this.bases[i].setMate(pair_table[i]);
        if (pair_table[i] > i)
            npairs++;
    }
    // must have at least 1 pair to avoid segfault
    if (npairs == 0){
        this.bases[1].setMate(this.nbase);
        this.bases[this.nbase].setMate(1);
    }
}

NAView.prototype.find_regions = function find_regions(){
    var i = null;
    var mate = null;
    var nb1 = null;

    nb1 = this.nbase + 1;
    var mark = [];
    for (i = 0; i < nb1; i++){
        mark.push(false);
    }
    this.nregion = 0;
    for (i = 0; i <= this.nbase; i++) {
        if ((mate = this.bases[i].getMate()) != 0 && !mark[i]) {
            this.regions[this.nregion].setStart1(i);
            this.regions[this.nregion].setEnd2(mate);
            mark[i] = true;
            mark[mate] = true;
            this.bases[i].setRegion(this.regions[this.nregion]);
            this.bases[mate].setRegion(this.regions[this.nregion]);
            for (i++, mate--; i < mate && this.bases[i].getMate() == mate; i++, mate--) {
                mark[mate] = true;
                mark[i]= true;
                this.bases[i].setRegion(this.regions[this.nregion]);
                this.bases[mate].setRegion(this.regions[this.nregion]);
            }
            this.regions[this.nregion].setEnd1(--i);
            this.regions[this.nregion].setStart2(mate + 1);

            this.nregion++;
        }
    }
}

NAView.prototype.construct_loop = function construct_loop(ibase){
    var i = null;
    var mate = null;
    var retloop = new Loop();
    var lp = new Loop();
    var cp = new Connection();
    var rp = new Region();
    var rlp = new Radloop();
    retloop = this.loops[this.loop_count++];
    retloop.setNconnection(0);
    retloop.setDepth(0);
    retloop.setNumber(this.loop_count);
    retloop.setRadius(0.0);

    for (rlp = this.rlphead; rlp != null; rlp = rlp.getNext())
        if (rlp.getLoopnumber() == this.loop_count)
            retloop.setRadius(rlp.getRadius());
    i = ibase;
    do {
        if ((mate = this.bases[i].getMate()) != 0) {
            rp = this.bases[i].getRegion();
            if (!this.bases[rp.getStart1()].isExtracted()) {
                if (i == rp.getStart1()) {
                    this.bases[rp.getStart1()].setExtracted(true);
                    this.bases[rp.getEnd1()].setExtracted(true);
                    this.bases[rp.getStart2()].setExtracted(true);
                    this.bases[rp.getEnd2()].setExtracted(true);
                    lp = this.construct_loop(rp.getEnd1() < this.nbase ? rp.getEnd1() + 1
                            : 0);
                } else if (i == rp.getStart2()) {
                    this.bases[rp.getStart2()].setExtracted(true);
                    this.bases[rp.getEnd2()].setExtracted(true);
                    this.bases[rp.getStart1()].setExtracted(true);
                    this.bases[rp.getEnd1()].setExtracted(true);
                    lp = this.construct_loop(rp.getEnd2() < this.nbase ? rp.getEnd2() + 1
                            : 0);
                } else {
                    console.log("Something went terribly wrong ....");
                }
                retloop.setNconnection(retloop.getNconnection() + 1);
                cp = new Connection();
                retloop.setConnection(retloop.getNconnection() - 1,	cp);
                retloop.setConnection(retloop.getNconnection(), null);
                cp.setLoop(lp);
                cp.setRegion(rp);
                if(i == rp.getStart1()) {
                    cp.setStart(rp.getStart1());
                    cp.setEnd(rp.getEnd2());
                } else {
                    cp.setStart(rp.getStart2());
                    cp.setEnd(rp.getEnd1());
                }
                cp.setExtruded(false);
                cp.setBroken(false);
                lp.setNconnection(lp.getNconnection() + 1);
                cp = new Connection();
                lp.setConnection(lp.getNconnection() - 1, cp);
                lp.setConnection(lp.getNconnection(), null);
                cp.setLoop(retloop);
                cp.setRegion(rp);
                if (i == rp.getStart1()) {
                    cp.setStart(rp.getStart2());
                    cp.setEnd(rp.getEnd1());
                } else {
                    cp.setStart(rp.getStart1());
                    cp.setEnd(rp.getEnd2());
                }
                cp.setExtruded(false);
                cp.setBroken(false);
            }
            i = mate;
        }
        if (++i > this.nbase)
            i = 0;
    } while (i != ibase);
    return retloop;
}

NAView.prototype.find_central_loop = function find_central_loop(){
    var lp = new Loop();
    var maxconn = null;
    var maxdepth = null;
    var i = null;

    determine_depths();
    maxconn = 0;
    maxdepth = -1;
    for (i = 0; i < this.loop_count; i++) {
        lp = this.loops[i];
        if (lp.getNconnection() > maxconn) {
            maxdepth = lp.getDepth();
            maxconn = lp.getNconnection();
            this.root = lp;
        } else if (lp.getDepth() > maxdepth
                && lp.getNconnection() == maxconn) {
            maxdepth = lp.getDepth();
            this.root = lp;
        }
    }
}

function determine_depths() {
    var lp = new Loop();
    var i = null;
    var j = null;

    for (i = 0; i < this.loop_count; i++) {
        lp = this.loops[i];
        for (j = 0; j < this.loop_count; j++){
            this.loops[j].setMark(false);
        }
        lp.setDepth(depth(lp));
    }
}

function depth(lp){
    var count = null;
    var ret = null;
    var d = null;

    if (lp.getNconnection() <= 1){
        return 0;
    }
    if (lp.isMark()){
        return -1;
    }
    lp.setMark(true);
    count = 0;
    ret = 0;
    for (var i = 0; lp.getConnection(i) != null; i++) {
        d = depth(lp.getConnection(i).getLoop());
        if (d >= 0) {
            if (++count == 1){
                ret = d;
            }
            else if (ret > d){
                ret = d;
            }
        }
    }
    lp.setMark(false);
    return ret + 1;
}

NAView.prototype.traverse_loop = function traverse_loop(lp, anchor_connection){
    var xs, ys, xe, ye, xn, yn, angleinc, r;
    var radius, xc, yc, xo, yo, astart, aend, a;
    var cp, cpnext, acp, cpprev;
    var i, j, n, ic;
    var da, maxang;
    var count, icstart, icend, icmiddle, icroot;
    var done, done_all_connections, rooted;
    var sign;
    var midx, midy, nrx, nry, mx, my, vx, vy, dotmv, nmidx, nmidy;
    var icstart1, icup, icdown, icnext, direction;
    var dan, dx, dy, rr;
    var cpx, cpy, cpnextx, cpnexty, cnx, cny, rcn, rc, lnx, lny, rl, ac, acn, sx, sy, dcp;
    var imaxloop = 0;

    angleinc = 2 * Math.PI / (this.nbase + 1);
    acp = null;
    icroot = -1;
    var indice = 0;

    for (ic = 0; (cp = lp.getConnection(indice)) != null; indice++, ic++) {
        xs = -Math.sin(angleinc * cp.getStart());
        ys = Math.cos(angleinc * cp.getStart());
        xe = -Math.sin(angleinc * cp.getEnd());
        ye = Math.cos(angleinc * cp.getEnd());
        xn = ye - ys;
        yn = xs - xe;
        r = Math.sqrt(xn * xn + yn * yn);
        cp.setXrad(xn / r);
        cp.setYrad(yn / r);
        cp.setAngle(Math.atan2(yn, xn));
        if (cp.getAngle() < 0.0){
            cp.setAngle(cp.getAngle() + 2 * Math.PI);
        }
        if (anchor_connection != null
                && anchor_connection.getRegion() == cp.getRegion()) {
            acp = cp;
            icroot = ic;
        }
    }
    set_radius: while (true) {
        this.determine_radius(lp, this.lencut);
        radius = lp.getRadius()/this.RADIUS_REDUCTION_FACTOR;
        if (anchor_connection == null){
            xc = yc = 0.0;
        }
        else {
            xo = (this.bases[acp.getStart()].getX() + this.bases
                    [acp.getEnd()].getX()) / 2.0;
            yo = (this.bases[acp.getStart()].getY() + this.bases
                    [acp.getEnd()].getY()) / 2.0;
            xc = xo - radius * acp.getXrad();
            yc = yo - radius * acp.getYrad();
        }

        // The construction of the connectors will proceed in blocks of
        // connected connectors, where a connected connector pairs means two
        // connectors that are forced out of the drawn circle because they
        // are too close together in angle.

        // First, find the start of a block of connected connectors

        if (icroot == -1){
            icstart = 0;
        }
        else {
            icstart = icroot;
        }
        cp = lp.getConnection(icstart);
        count = 0;
        done = false;
        do {
            j = icstart - 1;
            if (j < 0){
                j = lp.getNconnection() - 1;
            }
            cpprev = lp.getConnection(j);
            if (!this.connected_connection(cpprev, cp)) {
                done = true;
            }
            else {
                icstart = j;
                cp = cpprev;
            }
            if (++count > lp.getNconnection()) {
                // Here everything is connected. Break on maximum angular
                // separation between connections.
                maxang = -1.0;
                for (ic = 0; ic < lp.getNconnection(); ic++) {
                    j = ic + 1;
                    if (j >= lp.getNconnection()){
                        j = 0;
                    }
                    cp = lp.getConnection(ic);
                    cpnext = lp.getConnection(j);
                    ac = cpnext.getAngle() - cp.getAngle();
                    if (ac < 0.0){
                        ac += 2 * Math.PI;
                    }
                    if (ac > maxang) {
                        maxang = ac;
                        imaxloop = ic;
                    }
                }
                icend = imaxloop;
                icstart = imaxloop + 1;
                if (icstart >= lp.getNconnection()){
                    icstart = 0;
                }
                cp = lp.getConnection(icend);
                cp.setBroken(true);
                done = true;
            }
        } while (!done);
        done_all_connections = false;
        icstart1 = icstart;
        while (!done_all_connections) {
            count = 0;
            done = false;
            icend = icstart;
            rooted = false;
            while (!done) {
                cp = lp.getConnection(icend);
                if (icend == icroot){
                    rooted = true;
                }
                j = icend + 1;
                if (j >= lp.getNconnection()) {
                    j = 0;
                }
                cpnext = lp.getConnection(j);
                if (this.connected_connection(cp, cpnext)) {
                    if (++count >= lp.getNconnection()){
                        break;
                    }
                    icend = j;
                }
                else {
                    done = true;
                }
            }
            icmiddle = this.find_ic_middle(icstart, icend, anchor_connection,
                    acp, lp);
            ic = icup = icdown = icmiddle;
            done = false;
            direction = 0;
            while (!done) {
                if (direction < 0) {
                    ic = icup;
                }
                else if (direction == 0) {
                    ic = icmiddle;
                }
                else {
                    ic = icdown;
                }
                if (ic >= 0) {
                    cp = lp.getConnection(ic);
                    if (anchor_connection == null || acp != cp) {
                        if (direction == 0) {
                            astart = cp.getAngle()
                                    - Math.asin(1.0 / 2.0 / radius);
                            aend = cp.getAngle()
                                    + Math.asin(1.0 / 2.0 / radius);
                            this.bases[cp.getStart()].setX(
                                    xc + radius * Math.cos(astart));
                            this.bases[cp.getStart()].setY(
                                    yc + radius * Math.sin(astart));
                            this.bases[cp.getEnd()].setX(
                                    xc + radius * Math.cos(aend));
                            this.bases[cp.getEnd()].setY(
                                    yc + radius * Math.sin(aend));
                        }
                        else if (direction < 0) {
                            j = ic + 1;
                            if (j >= lp.getNconnection()){
                                j = 0;
                            }
                            cp = lp.getConnection(ic);
                            cpnext = lp.getConnection(j);
                            cpx = cp.getXrad();
                            cpy = cp.getYrad();
                            ac = (cp.getAngle() + cpnext.getAngle()) / 2.0;
                            if (cp.getAngle() > cpnext.getAngle()){
                                ac -= Math.PI;
                            }
                            cnx = Math.cos(ac);
                            cny = Math.sin(ac);
                            lnx = cny;
                            lny = -cnx;
                            da = cpnext.getAngle() - cp.getAngle();
                            if (da < 0.0){
                                da += 2 * Math.PI;
                            }
                            if (cp.isExtruded()) {
                                if (da <= Math.PI / 2){
                                    rl = 2.0;
                                }
                                else {
                                    rl = 1.5;
                                }
                            }
                            else {
                                rl = 1.0;
                            }
                            this.bases[cp.getEnd()].setX(
                                    this.bases[cpnext.getStart()].getX()
                                            + rl * lnx);
                            this.bases[cp.getEnd()].setY(
                                    this.bases[cpnext.getStart()].getY()
                                            + rl * lny);
                            this.bases[cp.getStart()].setX(
                                    this.bases[cp.getEnd()].getX() + cpy);
                            this.bases[cp.getStart()].setY(
                                    this.bases[cp.getEnd()].getY() - cpx);
                        } else {
                            j = ic - 1;
                            if (j < 0){
                                j = lp.getNconnection() - 1;
                            }
                            cp = lp.getConnection(j);
                            cpnext = lp.getConnection(ic);
                            cpnextx = cpnext.getXrad();
                            cpnexty = cpnext.getYrad();
                            ac = (cp.getAngle() + cpnext.getAngle()) / 2.0;
                            if (cp.getAngle() > cpnext.getAngle()){
                                ac -= Math.PI;
                            }
                            cnx = Math.cos(ac);
                            cny = Math.sin(ac);
                            lnx = -cny;
                            lny = cnx;
                            da = cpnext.getAngle() - cp.getAngle();
                            if (da < 0.0){
                                da += 2 * Math.PI;
                            }
                            if (cp.isExtruded()) {
                                if (da <= Math.PI / 2){
                                    rl = 2.0;
                                }
                                else {
                                    rl = 1.5;
                                }
                            }
                            else {
                                rl = 1.0;
                            }
                            this.bases[cpnext.getStart()].setX(
                                    this.bases[cp.getEnd()].getX() + rl
                                            * lnx);
                            this.bases[cpnext.getStart()].setY(
                                    this.bases[cp.getEnd()].getY() + rl
                                            * lny);
                            this.bases[cpnext.getEnd()].setX(
                                    this.bases[cpnext.getStart()].getX()
                                            - cpnexty);
                            this.bases[cpnext.getEnd()].setY(
                                    this.bases[cpnext.getStart()].getY()
                                            + cpnextx);
                        }
                    }
                }
                if (direction < 0) {
                    if (icdown == icend) {
                        icdown = -1;
                    }
                    else if (icdown >= 0) {
                        if (++icdown >= lp.getNconnection()) {
                            icdown = 0;
                        }
                    }
                    direction = 1;
                }
                else {
                    if (icup == icstart){
                        icup = -1;
                    }
                    else if (icup >= 0) {
                        if (--icup < 0) {
                            icup = lp.getNconnection() - 1;
                        }
                    }
                    direction = -1;
                }
                done = icup == -1 && icdown == -1;
            }
            icnext = icend + 1;
            if (icnext >= lp.getNconnection()){
                icnext = 0;
            }
            if (icend != icstart
                    && (!(icstart == icstart1 && icnext == icstart1))) {

                // Move the bases just constructed (or the radius) so that
                // the bisector of the end points is radius distance away
                // from the loop center.

                cp = lp.getConnection(icstart);
                cpnext = lp.getConnection(icend);
                dx = this.bases[cpnext.getEnd()].getX()
                        - this.bases[cp.getStart()].getX();
                dy = this.bases[cpnext.getEnd()].getY()
                        - this.bases[cp.getStart()].getY();
                midx = this.bases[cp.getStart()].getX() + dx / 2.0;
                midy = this.bases[cp.getStart()].getY() + dy / 2.0;
                rr = Math.sqrt(dx * dx + dy * dy);
                mx = dx / rr;
                my = dy / rr;
                vx = xc - midx;
                vy = yc - midy;
                rr = Math.sqrt(dx * dx + dy * dy);
                vx /= rr;
                vy /= rr;
                dotmv = vx * mx + vy * my;
                nrx = dotmv * mx - vx;
                nry = dotmv * my - vy;
                rr = Math.sqrt(nrx * nrx + nry * nry);
                nrx /= rr;
                nry /= rr;

                // Determine which side of the bisector the center should
                // be.

                dx = this.bases[cp.getStart()].getX() - xc;
                dy = this.bases[cp.getStart()].getY() - yc;
                ac = Math.atan2(dy, dx);
                if (ac < 0.0){
                    ac += 2 * Math.PI;
                }
                dx = this.bases[cpnext.getEnd()].getX() - xc;
                dy = this.bases[cpnext.getEnd()].getY() - yc;
                acn = Math.atan2(dy, dx);
                if (acn < 0.0){
                    acn += 2 * Math.PI;
                }
                if (acn < ac){
                    acn += 2 * Math.PI;
                }
                if (acn - ac > Math.PI){
                    sign = -1;
                }
                else {
                    sign = 1;
                }
                nmidx = xc + sign * radius * nrx;
                nmidy = yc + sign * radius * nry;
                if (rooted) {
                    xc -= nmidx - midx;
                    yc -= nmidy - midy;
                }
                else {
                    for (ic = icstart;;) {
                        cp = lp.getConnection(ic);
                        i = cp.getStart();
                        this.bases[i].setX(
                                this.bases[i].getX() + nmidx - midx);
                        this.bases[i].setY(
                                this.bases[i].getY() + nmidy - midy);
                        i = cp.getEnd();
                        this.bases[i].setX(
                                this.bases[i].getX() + nmidx - midx);
                        this.bases[i].setY(
                                this.bases[i].getY() + nmidy - midy);
                        if (ic == icend){
                            break;
                        }
                        if (++ic >= lp.getNconnection()){
                            ic = 0;
                        }
                    }
                }
            }
            icstart = icnext;
            done_all_connections = icstart == icstart1;
        }
        for (ic = 0; ic < lp.getNconnection(); ic++) {
            cp = lp.getConnection(ic);
            j = ic + 1;
            if (j >= lp.getNconnection()){
                j = 0;
            }
            cpnext = lp.getConnection(j);
            dx = this.bases[cp.getEnd()].getX() - xc;
            dy = this.bases[cp.getEnd()].getY() - yc;
            rc = Math.sqrt(dx * dx + dy * dy);
            ac = Math.atan2(dy, dx);
            if (ac < 0.0){
                ac += 2 * Math.PI;
            }
            dx = this.bases[cpnext.getStart()].getX() - xc;
            dy = this.bases[cpnext.getStart()].getY() - yc;
            rcn = Math.sqrt(dx * dx + dy * dy);
            acn = Math.atan2(dy, dx);
            if (acn < 0.0){
                acn += 2 * Math.PI;
            }
            if (acn < ac){
                acn += 2 * Math.PI;
            }
            dan = acn - ac;
            dcp = cpnext.getAngle() - cp.getAngle();
            if (dcp <= 0.0){
                dcp += 2 * Math.PI;
            }
            if (Math.abs(dan - dcp) > Math.PI) {
                if (cp.isExtruded()) {
                    console.log("Warning from traverse_loop. Loop "
                            + lp.getNumber() + " has crossed regions\n");
                }
                else if ((cpnext.getStart() - cp.getEnd()) != 1) {
                    cp.setExtruded(true);
                    continue set_radius; // remplacement du goto
                }
            }
            if (cp.isExtruded()) {
                this.construct_extruded_segment(cp, cpnext);
            }
            else {
                n = cpnext.getStart() - cp.getEnd();
                if (n < 0){
                    n += this.nbase + 1;
                }
                angleinc = dan / n;
                for (j = 1; j < n; j++) {
                    i = cp.getEnd() + j;
                    if (i > this.nbase){
                        i -= this.nbase + 1;
                    }
                    a = ac + j * angleinc;
                    rr = rc + (rcn - rc) * (a - ac) / dan;
                    this.bases[i].setX(xc + rr * Math.cos(a));
                    this.bases[i].setY(yc + rr * Math.sin(a));
                }
            }
        }
        break;
    }
    for (ic = 0; ic < lp.getNconnection(); ic++) {
        if (icroot != ic) {
            cp = lp.getConnection(ic);
            //IM HERE
            this.generate_region(cp);
            this.traverse_loop(cp.getLoop(), cp);
        }
    }
    n = 0;
    sx = 0.0;
    sy = 0.0;
    for (ic = 0; ic < lp.getNconnection(); ic++) {
        j = ic + 1;
        if (j >= lp.getNconnection()){
            j = 0;
        }
        cp = lp.getConnection(ic);
        cpnext = lp.getConnection(j);
        n += 2;
        sx += this.bases[cp.getStart()].getX()
                + this.bases[cp.getEnd()].getX();
        sy += this.bases[cp.getStart()].getY()
                + this.bases[cp.getEnd()].getY();
        if (!cp.isExtruded()) {
            for (j = cp.getEnd() + 1; j != cpnext.getStart(); j++) {
                if (j > this.nbase){
                    j -= this.nbase + 1;
                }
                n++;
                sx += this.bases[j].getX();
                sy += this.bases[j].getY();
            }
        }
    }
    lp.setX(sx / n);
    lp.setY(sy / n);
}

NAView.prototype.determine_radius = function determine_radius(lp, lencut){
    var mindit, ci, dt, sumn, sumd, radius, dit;
    var i, j, end, start, imindit = 0;
    var cp = new Connection(), cpnext = new Connection();
    var rt2_2 = 0.7071068;

    do {
        mindit = 1.0e10;
        for (sumd = 0.0, sumn = 0.0, i = 0; i < lp.getNconnection(); i++) {
            cp = lp.getConnection(i);
            j = i + 1;
            if (j >= lp.getNconnection()){
                j = 0;
            }
            cpnext = lp.getConnection(j);
            end = cp.getEnd();
            start = cpnext.getStart();
            if (start < end){
                start += this.nbase + 1;
            }
            dt = cpnext.getAngle() - cp.getAngle();
            if (dt <= 0.0){
                dt += 2 * Math.PI;
            }
            if (!cp.isExtruded()){
                ci = start - end;
            }
            else {
                if (dt <= Math.PI / 2){
                    ci = 2.0;
                }
                else {
                    ci = 1.5;
                }
            }
            sumn += dt * (1.0 / ci + 1.0);
            sumd += dt * dt / ci;
            dit = dt / ci;
            if (dit < mindit && !cp.isExtruded() && ci > 1.0) {
                mindit = dit;
                imindit = i;
            }
        }
        radius = sumn / sumd;
        if (radius < rt2_2){
            radius = rt2_2;
        }
        if (mindit * radius < lencut) {
            lp.getConnection(imindit).setExtruded(true);
        }
    } while (mindit * radius < lencut);
    if (lp.getRadius() > 0.0){
        radius = lp.getRadius();
    }
    else {
        lp.setRadius(radius);
    }
}

NAView.prototype.find_ic_middle = function find_ic_middle(icstart, icend, anchor_connection, acp, lp){
    var count, ret, ic, i;
    var done;

    count = 0;
    ret = -1;
    ic = icstart;
    done = false;
    while (!done) {
        if (count++ > lp.getNconnection() * 2) {
            console.log("Infinite loop in 'find_ic_middle'");
        }
        if (anchor_connection != null && lp.getConnection(ic) == acp) {
            ret = ic;
        }
        done = ic == icend;
        if (++ic >= lp.getNconnection()) {
            ic = 0;
        }
    }
    if (ret == -1) {
        for (i = 1, ic = icstart; i < (count + 1) / 2; i++) {
            if (++ic >= lp.getNconnection())
                ic = 0;
        }
        ret = ic;
    }
    return ret;
}

NAView.prototype.construct_extruded_segment = function construct_extruded_segment(cp, cpnext){
    var astart, aend1, aend2, aave, dx, dy, a1, a2, ac, rr, da, dac;
    var start, end, n, nstart, nend;
    var collision;

    astart = cp.getAngle();
    aend2 = aend1 = cpnext.getAngle();
    if (aend2 < astart){
        aend2 += 2 * Math.PI;
    }
    aave = (astart + aend2) / 2.0;
    start = cp.getEnd();
    end = cpnext.getStart();
    n = end - start;
    if (n < 0){
        n += this.nbase + 1;
    }
    da = cpnext.getAngle() - cp.getAngle();
    if (da < 0.0) {
        da += 2 * Math.PI;
    }
    if (n == 2) {
        this.construct_circle_segment(start, end);
    }
    else {
        dx = this.bases[end].getX() - this.bases[start].getX();
        dy = this.bases[end].getY() - this.bases[start].getY();
        rr = Math.sqrt(dx * dx + dy * dy);
        dx /= rr;
        dy /= rr;
        if (rr >= 1.5 && da <= Math.PI / 2) {
            nstart = start + 1;
            if (nstart > this.nbase){
                nstart -= this.nbase + 1;
            }
            nend = end - 1;
            if (nend < 0){
                nend += this.nbase + 1;
            }
            this.bases[nstart].setX(this.bases[start].getX() + 0.5 * dx);
            this.bases[nstart].setY(this.bases[start].getY() + 0.5 * dy);
            this.bases[nend].setX(this.bases[end].getX() - 0.5 * dx);
            this.bases[nend].setY(this.bases[end].getY() - 0.5 * dy);
            start = nstart;
            end = nend;
        }
        do {
            collision = false;
            this.construct_circle_segment(start, end);
            nstart = start + 1;
            if (nstart > this.nbase) {
                nstart -= this.nbase + 1;
            }
            dx = this.bases[nstart].getX() - this.bases[start].getX();
            dy = this.bases[nstart].getY() - this.bases[start].getY();
            a1 = Math.atan2(dy, dx);
            if (a1 < 0.0){
                a1 += 2 * Math.PI;
            }
            dac = a1 - astart;
            if (dac < 0.0){
                dac += 2 * Math.PI;
            }
            if (dac > Math.PI){
                collision = true;
            }
            nend = end - 1;
            if (nend < 0){
                nend += this.nbase + 1;
            }
            dx = this.bases[nend].getX() - this.bases[end].getX();
            dy = this.bases[nend].getY() - this.bases[end].getY();
            a2 = Math.atan2(dy, dx);
            if (a2 < 0.0){
                a2 += 2 * Math.PI;
            }
            dac = aend1 - a2;
            if (dac < 0.0){
                dac += 2 * Math.PI;
            }
            if (dac > Math.PI){
                collision = true;
            }
            if (collision) {
                ac = this.minf2(aave, astart + 0.5);
                this.bases[nstart].setX(
                        this.bases[start].getX() + Math.cos(ac));
                this.bases[nstart].setY(
                        this.bases[start].getY() + Math.sin(ac));
                start = nstart;
                ac = this.maxf2(aave, aend2 - 0.5);
                this.bases[nend].setX(this.bases[end].getX() + Math.cos(ac));
                this.bases[nend].setY(this.bases[end].getY() + Math.sin(ac));
                end = nend;
                n -= 2;
            }
        } while (collision && n > 1);
    }
}

NAView.prototype.construct_circle_segment = function construct_circle_segment(start, end){
    var dx, dy, rr, midx, midy, xn, yn, nrx, nry, mx, my, a;
    var l, j, i;

    dx = this.bases[end].getX() - this.bases[start].getX();
    dy = this.bases[end].getY() - this.bases[start].getY();
    rr = Math.sqrt(dx * dx + dy * dy);
    l = end - start;
    if (l < 0){
        l += this.nbase + 1;
    }
    if (rr >= l) {
        dx /= rr;
        dy /= rr;
        for (j = 1; j < l; j++) {
            i = start + j;
            if (i > this.nbase){
                i -= this.nbase + 1;
            }
            this.bases[i].setX(
                    this.bases[start].getX() + dx * j / l);
            this.bases[i].setY(
                    this.bases[start].getY() + dy * j / l);
        }
    }
    else {
        this.find_center_for_arc((l - 1), rr);
        dx /= rr;
        dy /= rr;
        midx = this.bases[start].getX() + dx * rr / 2.0;
        midy = this.bases[start].getY() + dy * rr / 2.0;
        xn = dy;
        yn = -dx;
        nrx = midx + this._h * xn;
        nry = midy + this._h * yn;
        mx = this.bases[start].getX() - nrx;
        my = this.bases[start].getY() - nry;
        rr = Math.sqrt(mx * mx + my * my);
        a = Math.atan2(my, mx);
        for (j = 1; j < l; j++) {
            i = start + j;
            if (i > this.nbase){
                i -= this.nbase + 1;
            }
            this.bases[i].setX(nrx + rr * Math.cos(a + j * this.angleinc));
            this.bases[i].setY(nry + rr * Math.sin(a + j * this.angleinc));
        }
    }
}

NAView.prototype.find_center_for_arc = function find_center_for_arc(n, b){
    var h, hhi, hlow, r, disc, theta, e, phi;
    var iter;

    hhi = (n + 1.0) / Math.PI;
    // changed to prevent div by zero if (ih)
    hlow = -hhi - b / (n + 1.000001 - b);
    if (b < 1){
        // otherwise we might fail below (ih)
        hlow = 0;
    }
    iter = 0;
    do {
        h = (hhi + hlow) / 2.0;
        r = Math.sqrt(h * h + b * b / 4.0);
        disc = 1.0 - 0.5 / (r * r);
        if (Math.abs(disc) > 1.0) {
            console.log("Unexpected large magnitude discriminant = " + disc
                            + " " + r);
        }
        theta = Math.acos(disc);
        phi = Math.acos(h / r);
        e = theta * (n + 1) + 2 * phi - 2 * Math.PI;
        if (e > 0.0) {
            hlow = h;
        }
        else {
            hhi = h;
        }
    } while (Math.abs(e) > 0.0001 && ++iter < this.MAXITER);
    if (iter >= this.MAXITER) {
        if (noIterationFailureYet) {
            console.log("Iteration failed in find_center_for_arc");
            noIterationFailureYet = false;
        }
        h = 0.0;
        theta = 0.0;
    }
    this._h = h;
    this.angleinc = theta;
}

NAView.prototype.generate_region = function generate_region(cp){
    var l, start, end, i, mate;
    var rp;

    rp = cp.getRegion();
    l = 0;
    if (cp.getStart() == rp.getStart1()) {
        start = rp.getStart1();
        end = rp.getEnd1();
    }
    else {
        start = rp.getStart2();
        end = rp.getEnd2();
    }
    if (this.bases[cp.getStart()].getX() > this.ANUM - 100.0
            || this.bases[cp.getEnd()].getX() > this.ANUM - 100.0) {
        console.log(
                "Bad region passed to generate_region. Coordinates not defined.");
    }
    for (i = start + 1; i <= end; i++) {
        l++;
        this.bases[i].setX(
                this.bases[cp.getStart()].getX() + this.HELIX_FACTOR * l
                        * cp.getXrad());
        this.bases[i].setY(
                this.bases[cp.getStart()].getY() + this.HELIX_FACTOR * l
                        * cp.getYrad());
        mate = this.bases[i].getMate();
        this.bases[mate].setX(
                this.bases[cp.getEnd()].getX() + this.HELIX_FACTOR * l
                        * cp.getXrad());
        this.bases[mate].setY(
                this.bases[cp.getEnd()].getY() + this.HELIX_FACTOR * l
                        * cp.getYrad());

    }
}

NAView.prototype.minf2 = function minf2(x1, x2) {
    return ((x1) < (x2)) ? (x1) : (x2);
}

NAView.prototype.maxf2 = function maxf2(x1, x2) {
    return ((x1) > (x2)) ? (x1) : (x2);
}

NAView.prototype.connected_connection = function connected_connection(cp, cpnext) {
    if (cp.isExtruded()) {
        return true;
    }
    else if (cp.getEnd() + 1 == cpnext.getStart()) {
        return true;
    }
    else {
        return false;
    }
}
