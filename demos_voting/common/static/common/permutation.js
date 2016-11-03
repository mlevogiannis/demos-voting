// Factorial, n-th permutation and original from n-th permutation functions.
// A sjcl version with division support is required.

function factorial(n) {

    var n = new sjcl.bn(n);
    var i = new sjcl.bn(2);
    var val = new sjcl.bn(1);

    while(n.greaterEquals(i)) {
        val = val.mul(i);
        i.addM(1);
    }

    return val;
}

function permute(iterable, index) {

    var seq = iterable.slice();
    var fact = factorial(seq.length);
    var perm = new Array();
    var next, index = (new sjcl.bn(index)).mod(fact);

    while (seq.length > 0) {

        fact = fact.div(seq.length);
        next = index.divmod(fact, index);
        item = seq.splice(parseInt(next.toString(), 16), 1);
        perm.push(item);
    }

    return perm;
}

function permute_ori(iterable, index) {

    var seq = iterable.slice();

    var fact = factorial(seq.length);
    var pos, index = (new sjcl.bn(index)).mod(fact);
    var next = new Array();

    for (var i = seq.length; i > 0; i--) {

        fact = fact.div(i);
        pos = index.divmod(fact, index);
        next.push(pos);
    }

    var pos, item;
    var perm = new Array();

    for (var i = seq.length - 1; i >= 0; i--) {
        pos = next[i];
        item = seq[i];
        perm.splice(pos, 0, item)
    }

    return perm;
}

