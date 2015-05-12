// Start/end datetimepickers ---------------------------------------------------

$("#start-datetimepicker").datetimepicker({
	format: time_format,
	locale: $("html").attr("lang"),
	minDate: moment().add(1, "minutes"),
	useCurrent: false,
	sideBySide: true,
});

$("#end-datetimepicker").datetimepicker({
	format: time_format,
	locale: $("html").attr("lang"),
	minDate: moment().add(2, "minutes"),
	useCurrent: false,
	sideBySide: true
});

$("#start-datetimepicker").on("dp.change", function(e) {
	date = moment(e.date).add(1, "minutes");
	$("#end-datetimepicker").data("DateTimePicker").minDate(date);
});

$("#end-datetimepicker").on("dp.change", function(e) {
	date = moment(e.date).subtract(1, "minutes");
	$("#start-datetimepicker").data("DateTimePicker").maxDate(date);
});

// Question sortable table -----------------------------------------------------

$("#question-table tbody").sortable({
	update: function(event, ui) {
		update_question_table()
	}
});

// Question control buttons ----------------------------------------------------

$("#question-add").click(function(e) {
	
	// Clone base question (identified by __prefix__)
	
	var question = $(".question[data-index='__prefix__']").clone(true);
	var question_entry = $(".question-entry[data-index='__prefix__']").clone(true);
	
	question.removeClass("hidden");
	question_entry.removeClass("hidden");
	
	question.appendTo("form");
	question_entry.insertBefore(".question-entry:last");
	
	// Update question table and option list
	
	update_question_table();
	update_option_list(question);
	
	// Register sortable widget
	
	question.find("ul").sortable({
		handle: ".option-handle",
		start: function(event, ui) {
			$(this).find(".input-group").focusout();
		},
		update: function(event, ui) {
			update_option_list($(this).parent(".question"));
		},
	});
	
	question.find(".question-cancel").prop("disabled", true);
	show_question(question);
});

var question_fields = ["question"];

$(".question-edit").click(function(e) {
	
	var question_entry = $(this).closest(".question-entry");
	var index = question_entry.attr("data-index");
	var question = $(".question[data-index='" + index + "']");
	
	// Store a copy of question text and options
	
	var options = [];
	
	question.find(".option input").each(function() {
		options.push($(this).val());
	});
	
	question.data("options", options);
	question.data("question", question.find("input:first").val());
	
	question.find(".question-cancel").prop("disabled", false);
	show_question(question);
});

$(".question-delete").click(function(e) {
	
	var question = $(this).closest(".question");
	var index = question.attr("data-index");
	var question_entry = $(".question-entry[data-index='" + index + "']");
	
	// Delete question and its table entry
	
	question.removeData();
	question_entry.remove();
	update_question_table();
	
	hide_question(question, function() {
		question.remove();
	});
});

$(".question-cancel").click(function(e) {
	
	var question = $(this).closest(".question");
	var index = question.attr("data-index");
	var question_entry = $(".question-entry[data-index='" + index + "']");
	
	// Ensure we have exactly the required number of options
	
	var options = question.data("options");
	
	while (question.find(".option").length > options.length) {
		question.find(".option:last").remove();
	}
	
	while (question.find(".option").length < options.length) {
		var last_option = question.find(".option:last");
		last_option.clone(true).insertAfter(last_option);
	}
	
	update_option_list(question);
	
	// Restore question text and options
	
	question.find(".option input").each(function(index) {
		remove_error.call($(this));
		$(this).val(options[index]);
	});
	
	question.find("input:first").val(question.data("question"));
	
	question.removeData();
	hide_question(question);
});

$(".question-save").click(function(e) {
	
	var question = $(this).closest(".question");
	var index = question.attr("data-index");
	var question_entry = $(".question-entry[data-index='" + index + "']");
	
	// Update question's table entry
	
	var value = question.find("input:first").val();
	question_entry.children("td:first").text(value);
	
	question.removeData();
	hide_question(question);
});

// Question order update -------------------------------------------------------

function update_question_table() {
	
	// Create a map of the questions to be updated
	
	var question_table = $(".question-entry:not(:last)").map(function() {
		
		var question_entry = $(this);
		
		var new_index = question_entry.index();
		var old_index = question_entry.attr("data-index");
		
		// If the index has not changed, ignore the question
		
		if (old_index == new_index)
			return null;
		
		// Otherwise, mark the question for update
		
		var dict = {
			
			"question": $("form .question[data-index='" + old_index + "']"),
			"question_entry": question_entry,
		    "new_index": new_index,
		};
		
		return dict;
	});
	
	// Update each question of the question table
	
	question_table.each(function() {
		
		var question = this["question"];
		var question_entry = this["question_entry"];
		var new_index = this["new_index"];
		
		// Update the question's indexes
		
		question.attr("data-index", new_index);
		question_entry.attr("data-index", new_index);
		
		// Function to replace 'old_index' or '__prefix__' with 'new_index'
		
		function replace_f(field, field_attr, field_index) {
			
			field.attr(field_attr, function(index, attr) {
				
				// Updates question's index or option's prefix
				
				var re = /(question-|option)(?:__prefix__|\d+)/;
				return attr.replace(re, "$1" + field_index);
			});
		}
		
		// Update 'id', 'name' and 'for' attributes
		
		question.find("input").each(function(e) {
			replace_f($(this), "id", new_index);
			replace_f($(this), "name", new_index);
		});
		
		question.find("label").each(function(e) {
			replace_f($(this), "for", new_index);
		});
		
		// Update table's first column
		
		question_entry.children("th").text(new_index + 1);
	});
	
	// Update TOTAL_FORMS value and add-button's state
	
	var maximum = management_form_max("question");
	var current = $(".question-entry:not(:last)").length;
	
	management_form_total("question", current);
	$("#question-add").prop("disabled", !(current < maximum));
}

// Question show/hide functions ------------------------------------------------

function show_question(question, complete_f) {
	
	var election = $("#election");
	var question_table = $("#question-table");
	
	election.hide(400);
	question_table.hide(400);
	
	question.show({
		duration: 400,
		complete: function() {
			
			$('html, body').animate({
				scrollTop: question.offset().top
			}, "slow");
			
			if (typeof complete_f !== "undefined")
				complete_f();
		}
	});
}

function hide_question(question, complete_f) {
	
	var election = $("#election");
	var question_table = $("#question-table");
	
	question.hide(400);
	election.show(400);
	
	question_table.show({
		duration: 400,
		complete: function() {
			
			$('html, body').animate({
				scrollTop: question_table.offset().top
			}, "slow");
			
			if (typeof complete_f !== "undefined")
				complete_f();
		}
	});
}

// Option control buttons ----------------------------------------------------

$(".option-add").click(function(e) {
	
	var question = $(this).closest(".question");
	var option_prefix = "option" + question.attr("data-index");
	
	// Check if a new option can be added
	
	var option_max = management_form_max(option_prefix);
	var option_total = management_form_total(option_prefix);
	
	if (option_total >= option_max)
		return;

	// Clone and clear selected option
		
	var cur_option = $(this).closest(".option");
	var new_option = cur_option.clone(true);
	
	var new_option_input = new_option.find("input");
	
	new_option_input.val("");
	remove_error.call(new_option_input);
	new_option.insertAfter(cur_option);
	
	update_option_list(question);
});

$(".option-delete").click(function(e) {
	
	var option = $(this).closest(".option");
	var question = $(this).closest(".question");
	
	var option_prefix = "option" + question.attr("data-index");
	
	// Check if the option can be removed
	
	var option_min = management_form_min(option_prefix);
	var option_total = management_form_total(option_prefix);
	
	if (option_total <= option_min)
		return;
	
	// Remove selected option
	
	option.remove();
	update_option_list(question);
});

// Option order update -------------------------------------------------------

function update_option_list(question) {
	
	var option_list = question.find(".option");
	var option_prefix = "option" + question.attr("data-index");
	
	// Update each option in the option list
	
	option_list.each(function() {
		
		var option = $(this);
		var new_index = option.index();
		
		// Function to replace 'old_index' with 'new_index'
		
		function replace_f(field, field_attr, field_index) {
			
			field.attr(field_attr, function(index, attr) {
				
				// Update option's index
				
				var re = /(option(?:__prefix__|\d+)-)\d+/;
				return attr.replace(re, "$1" + field_index);
			});
		}
		
		// Update 'id', 'name' and 'for' attributes
		
		option.find("input").each(function(e) {
			replace_f($(this), "id", new_index);
			replace_f($(this), "name", new_index);
		});
		
		option.find("label").each(function(e) {
			replace_f($(this), "for", new_index);
		});
		
		// Update labels
		
		var labels = option.find("label").add(option.find("input").prev());
		
		labels.each(function(e) {
			$(this).text($(this).text().replace(/\d+/, new_index + 1));
		});
	});
	
	// Update TOTAL_FORMS value
	
	management_form_total(option_prefix, option_list.length);
}

// ManagementForm functions ----------------------------------------------------

function management_form_total(prefix, value) {
	
	// Return or update ManagementForm's TOTAL_FORMS value
	
	var total_forms = $("#id_" + prefix + "-TOTAL_FORMS");
	
	if (typeof value !== "undefined")
		total_forms.val(value);
	
	return parseInt(total_forms.val());
}

function management_form_min(prefix) {
	
	// Return ManagementForm's MIN_NUM_FORMS value
	
	return parseInt($("#id_" + prefix + "-MIN_NUM_FORMS").val());
}

function management_form_max(prefix) {
	
	// Return ManagementForm's MAX_NUM_FORMS value
	
	return parseInt($("#id_" + prefix + "-MAX_NUM_FORMS").val());
}

// Error handlers --------------------------------------------------------------

$(".question-edit").one("click", remove_danger);
$(".form-group").find(".date").one("dp.change", remove_error);
$(".form-group").find("input, select").one("change", remove_error);

function remove_error(e) {
	
	var form_group = $(this).closest(".form-group");
	var popover = form_group.find("[data-toggle='popover']");
	
	popover.popover("disable");
	form_group.removeClass("has-error");
}

function remove_danger(e) {
	
	$(this).closest("tr").removeClass("danger");
}

$("[data-toggle='popover']").popover({
	html: true,
	trigger: "focus",
	placement: function(popover, element) {
		
		if (window.matchMedia && window.matchMedia("(min-width: 992px)").matches)
			return $(element).attr("data-placement");
		
		return "top";
	},
});

// -----------------------------------------------------------------------------

$(document).ready(function() {
	
	// Update questions and options
	
	update_question_table();
	
	$("form .question").each(function() {
		
		update_option_list($(this));
		
		// Register sortable widget
		
		$(this).find("ul").sortable({
			handle: ".option-handle",
			start: function(event, ui) {
				$(this).find(".input-group").focusout();
			},
			update: function(event, ui) {
				update_option_list($(this).parent(".question"));
			},
		});
	});
});

