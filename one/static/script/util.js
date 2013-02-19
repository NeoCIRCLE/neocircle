var cloud = (function(cloud) {
    /**
     * Convert bytes to human readable format
     */
    cloud.convert = function(n, skip, precision) {
        skip = skip | 0;
        precision = precision | 2;
        var suffix = 'B KB MB GB'.split(' ');
        for(var i = skip; n > 1024; i++) {
            n /= 1024;
        }
        return n.toFixed(precision) + ' ' + suffix[i];
    }

    /**
     * Returns throttled function
     */
    cloud.throttle = function(f) {
        var disabled = false;
        return function() {
            if(disabled) {
                return
            };
            disabled = true;
            setTimeout(function() {
                disabled = false;
            }, 700);
            f.apply(this, arguments);
        }
    }

    /**
     * Delay the function call for `f` until `g` evaluates true
     * Default check interval is 1 sec
     */
    cloud.delayUntil = function(f, g, timeout) {
        var timeout = timeout || 1000;

        function check() {
            var o = arguments;
            if(!g()) {
                setTimeout(function() {
                    check.apply(null, o)
                }, timeout);
                return;
            }
            f.apply(null, o);
        }
        return function() {
            check.apply(null, arguments);
        }
    }
})(cloud || {});
