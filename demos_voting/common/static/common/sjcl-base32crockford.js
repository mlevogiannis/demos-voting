sjcl.codec.base32crockford = {
    
    symbols: "0123456789ABCDEFGHJKMNPQRSTVWXYZ",
    
    fromBits: function(arr, hyphens) {
        
        var num = sjcl.bn.fromBits(arr);
        var chars = sjcl.codec.base32crockford.symbols;
        var out = num ? "" : "0";
        
        if (num < 0)
            throw new sjcl.exception.invalid("argument is not a non-negative integer");
        
        if (typeof hyphens === "undefined")
            hyphens = -1;
        
        while (num.greaterEquals(0) && !num.equals(0)) {
            
            // d = num / 32
            
            d = new sjcl.bn(num);
            
            for (var s = 0; s < 5; s++)
                d.halveM();
            
            // m = num % 32
            
            m = new sjcl.bn(d);
            
            for (var s = 0; s < 5; s++)
                m.doubleM();
            
            m = num.sub(m);
            
            out = chars[parseInt(m.toString()) || 0] + out;
            num = d;
        }
        
        if (hyphens > 0)
            out = sjcl.codec.base32crockford.hyphen(out, hyphens);
        
        return out;
    },
    
    toBits: function(str) {
        
        var i, c, len;
        var out = new sjcl.bn();
        var chars = sjcl.codec.base32crockford.symbols;
        
        str = sjcl.codec.base32crockford.normalize(str);
        str = sjcl.codec.base32crockford.hyphen(str, 0);
        
        for (i = 0, len = str.length; i < len; i++) {
            
            c = str.charAt(i);
            
            // out = out * 32
            
            for (var s = 0; s < 5; s++)
                out.doubleM();
            
            out.addM(chars.indexOf(c));
        }
        
        return out.toBits();
    },
    
    normalize: function(str, hyphens) {
        
        str = str.toUpperCase();
        str = str.split("O").join("0");
        str = str.split("I").join("1");
        str = str.split("L").join("1");
        
        var regex = new RegExp("^[" + sjcl.codec.base32crockford.symbols + "-" + "]*$");
    
        if (!regex.test(str))
            throw new sjcl.exception.invalid("Non-base32crockford digit found");
        
        if (typeof hyphens === "undefined")
            hyphens = -1;
        
        if (hyphens > 0)
            out = sjcl.codec.base32crockford.hyphen(out, hyphens);
        
        return str;
    },
    
    hyphen: function(str, hyphens) {
        
        if (hyphens >= 0)
            str = str.replace(/[-]/g, '');
        
        if (hyphens > 0)
            str = str.match(new RegExp(".{1," + hyphens + "}", "g")).join("-");
        
        return str;
    },
};

