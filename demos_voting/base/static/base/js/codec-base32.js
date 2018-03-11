base32 = {
    // Reference: http://www.crockford.com/wrmg/base32.html
    chars: "0123456789ABCDEFGHJKMNPQRSTVWXYZ",
    regex: "(?!-)(?:-?[0-9A-TV-Za-tv-z])",

    // Convert from a bitArray to a Crockford's Base32 string.
    fromBits: function(arr, length, groupLength) {
        var encoded;
        var n = sjcl.bn.fromBits(arr);
        if (!n.greaterEquals(0)) {
            throw new sjcl.exception.invalid("'" + n + "' is not a non-negative integer.");
        } else if (n.equals(0)) {
            encoded = "0";
        } else {
            encoded = "";
            while (n.greaterEquals(0) && !n.equals(0)) {
                var r = parseInt(n.mod(32).toString(), 16);
                encoded = base32.chars[r] + encoded;
                for (var i = 0; i < 5; i++) {
                    n.halveM();
                }
            }
        }
        if (typeof length !== "undefined") {
            while (encoded.length < length) {
                encoded = "0" + encoded;
            }
        }
        if (typeof groupLength !== "undefined") {
            encoded = base32.hyphenate(encoded, groupLength);
        }
        return encoded;
    },

    // Convert from a Crockford's Base32 string to a bitArray.
    toBits: function(encoded) {
        encoded = base32.normalize(encoded);
        var n = new sjcl.bn();
        for (var c = 0, len = encoded.length; c < len; c++) {
            for (var i = 0; i < 5; i++) {
                n.doubleM();
            }
            n.addM(base32.chars.indexOf(encoded.charAt(c)));
        }
        return n.toBits();
    },

    // Validate a Crockford's Base32 encoded string.
    validate: function(encoded) {
        var validation_regex = new RegExp("^" + base32.regex + "*$");
        return validation_regex.test(encoded);
    },

    // Normalize a Crockford's Base32 encoded string.
    normalize: function(encoded) {
        return encoded.toUpperCase().split("O").join("0").split("I").join("1").split("L").join("1").split("-").join("");
    },

    // Hyphenate a Crockford's Base32 encoded string.
    hyphenate: function(encoded, groupLength) {
        if (groupLength < 0) {
            throw new sjcl.exception.invalid("'" + groupLength + "' is not a non-negative integer.");
        } else {
            encoded = encoded.replace(/[-]/g, '');
            if (groupLength > 0) {
                var regex = new RegExp(".{1," + groupLength + "}", "g");
                encoded = encoded.match(regex).join("-");
            }
        }
        return encoded;
    },
};
