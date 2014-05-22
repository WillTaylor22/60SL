$("#feedback_button").click(function() {
	var feedback_content = $("#feedback").val();
	if(feedback_content != ''){
		$.ajax({
			url: "/feedback",
        	type: "POST",
        	data: ({
               feedback_content: feedback_content
               feedback
           }),
        	success: function(data) 
          {
          	$("#feedback").val("");
          	$("#feedback").attr("placeholder", "Thanks!");;
          }
		})
	}
})