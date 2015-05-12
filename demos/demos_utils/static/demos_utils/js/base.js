$(document).ready(function() {
	
	/* Manually handle sticky footer if css flex is not supported */
	
	if (!(("-webkit-flex-direction" in document.body.style
	 || "-moz-flex-direction" in document.body.style
	 || "flex-direction" in document.body.style)
	 && ("-webkit-flex" in document.body.style
	 || "-moz-flex" in document.body.style
	 || "-ms-flex" in document.body.style
	 || "flex" in document.body.style))) {
		
		var bodyHeight = $("body").height();
		var windowHeight = $(window).height();
		if (windowHeight > bodyHeight) {
			$("footer").css("position", "absolute").css("bottom", 0);
		}
	}
});

// Numeric input in textbox ----------------------------------------------------

$(".number-input").change(function(e) {
	
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

// Text input with checkbox ----------------------------------------------------

$(".checkbox-text").find("input[type='checkbox']").change(function(e) {
	
	var input_parent = $(this).closest(".checkbox-text");
	
	var input_checkbox = $(this);
	var input_text = input_parent.find("input[type='text']");
	
	var checked = input_checkbox.prop("checked");
	input_text.prop("disabled", !checked);
});

$(".checkbox-text").find("input[type='checkbox']").trigger("change");

// Select placeholder ----------------------------------------------------------

$(".select-placeholder").change(function(e) {
	
	if (!($(this).children("option:first-child").is(":selected")))
		$(this).css("color", "#555");
	else
		$(this).css("color", "#999");
});

$(".select-placeholder").trigger("change");

