$("#feedback_button").click(function() {
	var feedback_content = $("#feedback").val();
	var feedback_page = $("#meta").val();
  if(feedback_content != ''){
		$.ajax({
			url: "/feedback",
        	type: "POST",
        	data: ({
               feedback_content: feedback_content,
               feedback_page: feedback_page
           }),
        	success: function(data) 
          {
          	$("#feedback").val("");
          	$("#feedback").attr("placeholder", "Thanks!");;
          }
		})
	}
})