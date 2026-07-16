// static/src/js/phone-mask.js
(function() {
    function formatPhone(value) {
        var d = (value || '').replace(/\D/g, '');
        if (!d) return '';
        if (d[0] === '8') d = '7' + d.slice(1);
        else if (d[0] !== '7') d = '7' + d;
        d = d.slice(0, 11);
        var r = d.slice(1), out = '+7';
        if (r.length) out += ' (' + r.slice(0, 3);
        if (r.length >= 3) out += ') ' + r.slice(3, 6);
        if (r.length >= 6) out += '-' + r.slice(6, 8);
        if (r.length >= 8) out += '-' + r.slice(8, 10);
        return out.replace(/[\s()\-]+$/, '');
    }

    document.querySelectorAll('.phone-input').forEach(function(inp) {
        inp.addEventListener('input', function() {
            inp.value = formatPhone(inp.value);
        });
        if (inp.value) inp.value = formatPhone(inp.value);
    });
})();