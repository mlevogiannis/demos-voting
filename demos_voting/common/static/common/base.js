// Set current locale ----------------------------------------------------------

moment.locale($("html").attr("lang"));

// ISO8601 to local date and time conversion -----------------------------------

$(".datetime-iso8601").each(function(index, element) {

    var element = $(element);
    var format = element.data("format");
    var datetime = moment(element.text());

    if (datetime.isValid()) {
        element.text(datetime.format(format));
    }
});

// Election ID input -----------------------------------------------------------

$(".election-id-input").click(function(e) {

    var modal = $("#election-id-modal");
    var input = modal.find("input");

    input.val("");
    input.trigger("change");
    input.data("href", $(this).attr("href"));

    modal.find(".modal-title").text($(this).html().replace(/<.*>/, ""));
    modal.modal("show");

    modal.on("shown.bs.modal", function(e) {
        input.focus();
    });

    return false;
});

$("#election-id-modal button:last").click(function(e) {

    var modal = $("#election-id-modal");
    var input = modal.find("input");

    var value = input.val();

    if (!value) {
        input.parent(".form-group").addClass("has-warning has-feedback");
        input.siblings(".form-control-feedback").removeClass("hidden");
        input.css("text-indent", "30px");
        input.focus();
    }
    else {
        modal.find("button").add(input).prop("disabled", true);
        modal.find(".progress").closest(".row").removeClass("hidden");
        window.location.href = input.data("href") + value.toUpperCase() + "/";
    }
});

$("#election-id-modal input").on("input change remove", function(e) {

    var input = $(this);

    input.parent(".form-group").removeClass("has-warning has-feedback");
    input.siblings(".form-control-feedback").addClass("hidden");
    input.css("text-indent", "0px");
});

$("#election-id-modal input").keypress(function(e) {

    if (e.which == 13) {
        $(this).closest(".modal").find("button:last").click();
    }
});

// Election box ----------------------------------------------------------------

$(document).ready(function() {

    var time = $(".election-box > .header > .time");

    if (!time.length)
        return;

    var span = time.children(".text");

    // common values

    span.data("start-datetime", moment(span.data("start-datetime")));
    span.data("end-datetime", moment(span.data("end-datetime")));

    span.data("now-difftime", moment().diff(span.data("now-datetime")));

    // tooltip

    var datetime = time.find(".datetime");

    var t1 = datetime.children(":first-child").text();
    var t2 = datetime.children(":last-child").text();

    var t1_split = t1.split(",");
    var t2_split = t2.split(",");

    time.tooltip({
        placement: "bottom",
        container: ".election-box > .header",
        title: t1 + " - " + ((t1_split[0] == t2_split[0]) ? t2_split[1] : t2),
    });

    update_election_box_time();
});

function update_election_box_time() {

    var span = $(".election-box > .header > .time > .text");

    var start_datetime = span.data("start-datetime");
    var end_datetime = span.data("end-datetime");
    var now_datetime = moment().add(span.data("now-difftime"), "ms");

    var t1, t2, msg, to;

    // Select the appropriate message

    if (now_datetime < start_datetime) {

        t1 = now_datetime;
        t2 = start_datetime;

        to = t1.to(t2, true);
        msg = "starts-msg";

    } else if (now_datetime >= end_datetime) {

        t1 = end_datetime;
        t2 = now_datetime;

        to = t1.to(t2, true);
        msg = "ended-msg";

    } else {

        t1 = now_datetime;
        t2 = end_datetime;

        to = t1.to(t2, true);
        msg = (to.match(/\d+/g) != null) ? "remaining-p-msg" : "remaining-s-msg";
    }

    span.text(span.data(msg).replace("%s", to));

    // Schedule next message update

    var timeout, diff = Math.abs(t1.diff(t2, "s"));

    if (diff < 45)
        timeout = diff;
    else if (diff < 45 * 60)
        timeout = 60;
    else if (diff < 22 * 60 * 60)
        timeout = 60 * 60;
    else
        timeout = 24 * 60 * 60;

    window.setTimeout(update_election_box_time, timeout * 1000);
}

// Numeric input in textbox ----------------------------------------------------

$(".input-type-number").on("change update", function(e) {

    var input = $(this);

    var new_value = input.val();
    var value = input.data("value") || "";

    var min_value = parseInt(input.prop("min"));
    var max_value = parseInt(input.prop("max"));

    // Restore old value if new value is not a number or out of range

    if (new_value && /^\d*$/.test(new_value)) {

        new_value = parseInt(new_value);

        if ((!min_value || new_value >= min_value)
        && (!max_value || new_value <= max_value))
            value = new_value;
    }
    else if (!new_value) value = "";

    input.val(value);
    input.data("value", value);
});

$(".number-input").trigger("change");

// Select placeholder ----------------------------------------------------------

$(".select-placeholder").on("change update", function(e) {

    var color = $(this).children("option:first-child").is(":selected") ? "#999" : "#555";
    $(this).css("color", color);

}).trigger("change");

// Event debounce --------------------------------------------------------------

var debounce = function (func, threshold, execAsap) {

    // http://www.paulirish.com/2009/throttled-smartresize-jquery-event-handler/
    // http://unscriptable.com/index.php/2009/03/20/debouncing-javascript-methods/

    var timeout;

    return function debounced () {
        var obj = this;
        function delayed () {
            if (!execAsap)
                func.apply(obj);
            timeout = null;
        };

        if (timeout)
            clearTimeout(timeout);
        else if (execAsap)
            func.apply(obj);

        timeout = setTimeout(delayed, threshold || 100);
    };
}

// Pad a numeric string on the left with zero digits ---------------------------

function zfill(num, width) {

    var val = Math.abs(num);
    var sign = (num < 0) ? "-" : "";

    var zeros_count = Math.max(0, width - Math.floor(val).toString().length);
    var zeros = Array(zeros_count + 1).join("0");

    return sign + zeros + val;
}

// Parse cookie, CSRF token value ----------------------------------------------

function getCookie(name) {

    // https://docs.djangoproject.com/en/1.8/ref/csrf/#ajax

    var cookieValue = null;
    if (document.cookie && document.cookie != "") {
        var cookies = document.cookie.split(";");
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + "=")) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

var csrfmiddlewaretoken = getCookie("csrftoken");

// Default spinner options -----------------------------------------------------

var def_spinner_opts = {
    lines: 13, // The number of lines to draw
    length: 28, // The length of each line
    width: 14, // The line thickness
    radius: 42, // The radius of the inner circle
    scale: 1, // Scales overall size of the spinner
    corners: 1, // Corner roundness (0..1)
    color: '#000', // #rgb or #rrggbb or array of colors
    opacity: 0.25, // Opacity of the lines
    rotate: 0, // The rotation offset
    direction: 1, // 1: clockwise, -1: counterclockwise
    speed: 1, // Rounds per second
    trail: 60, // Afterglow percentage
    fps: 20, // Frames per second when using setTimeout() as a fallback for CSS
    zIndex: 2e9, // The z-index (defaults to 2000000000)
    className: 'spinner', // The CSS class to assign to the spinner
    top: '50%', // Top position relative to parent
    left: '50%', // Left position relative to parent
    shadow: false, // Whether to render a shadow
    hwaccel: false, // Whether to use hardware acceleration
    position: 'absolute', // Element positioning
}
