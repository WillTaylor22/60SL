// functionality:
// The page has 4 interactive functions:
// you can leave a review (not in this version)
// you can add an item to the cart (or increase the quantity)
//   with a + button from the menu
// ---> the item appears in the cart at the bottom
// you can change the quantity of the items in the cart using +/- buttons
// you can go to the "review order" page by hitting "order" 

var cart = new Array(); // id, cat, item, subitem, price OR pricemin, turnaround, qty
var runningtotal = 0
var formattedtotal = 0

$(document).ready(function(){
	build_cart_html_table()	
})

// this adds an item to the basket
// takes all the info it needs from the HTML in the page - no server queries!

function item_added(id, cat, item, subitem, price, pricemin, turnaround, amount){ 
	// check if item is in cart
	// if item exists, get it's index in the cart array. Otherwise returns -1
	var myIndex = cart.map(function(cart){return cart[0];}).indexOf(id)
	
	// update cart array
	if(myIndex!=-1)
		change_quantity_by_id(id, amount) 
	else{
		var cart_price = Math.max(price,pricemin)

		cart.push(
		[id,
		cat,
		item,
		subitem,
		cart_price,
		turnaround,
		1])

		add_to_total(cart_price)

		cart.sort(_sortFunction)
		build_cart_html_table()
	}
	print_cart_to_console()
}

function _sortFunction(a, b){
    return a[0] > b[0];
}

function print_cart_to_console(){
	console.log("cart -----");
	for (var i=0; i<cart.length; i++){
		console.log(cart[i]);
	}
}


function change_quantity_by_id(id, change){
	var myIndex = cart.map(function(cart){return cart[0];}).indexOf(id)
	
	cart[myIndex][6] += change
	add_to_total(cart[myIndex][4]*change)

	if (cart[myIndex][6] <= 0) {
		cart.splice(myIndex, 1);
	}
	build_cart_html_table()
}

function add_to_total(amount){
	runningtotal += amount
	formattedtotal = accounting.formatMoney(runningtotal, "£ ", 2)
}

function build_cart_html_table(){

	// clear old table
	var tablediv = document.getElementById("ordertablediv")
	tablediv.innerHTML = ""

	// tablediv>table>tablebody>tablerow>tabledata

	//setup table
	var tbl=document.createElement('table');
	tbl.id = 'ordertable'
	tbl.style = 'width: 100%;'

	var tbdy=document.createElement('tbody');
	
	// create table rows
	// for each item in the cart, check to see if the item already exists
	// first, we need to add a "category row" if that category doesn't exist
	// current categories

    // use a temporary array to remember previous categories in the html table.
	var categories_in_table = new Array();

	for(var i=0; i<cart.length; i++){ //for each item in the cart...
	    // check to see if category already present in table
	    var myIndex = categories_in_table.indexOf(cart[i][1]) 

	    //add current category done AFTER search through previous
	    categories_in_table.push(cart[i][1]) 

	    // adding "category row"
	    var tr=document.createElement('tr');
		if(myIndex==-1){    //new category row
			var td=document.createElement('th');
			td.appendChild(document.createTextNode(cart[i][1]))
			tr.appendChild(td);
			tbdy.appendChild(tr);
		}
		
		// adding row for item
		var tr = create_item_row(i)
		tbdy.appendChild(tr)
	}

	var th = create_total_row()
	tbdy.appendChild(th);
	
	tbl.appendChild(tbdy);
	tablediv.appendChild(tbl)

	add_total_to_title()

	add_custom_button(tablediv)

	add_order_button(tablediv)
}

function add_custom_button(tablediv){
	tablediv.appendChild(document.createElement("br"))
	var CustomButton = document.createElement("button")
	var t = document.createTextNode("Add Custom Item")
	var CustomButtonIcon = document.createElement("span")
	CustomButtonIcon.className = "glyphicon glyphicon-plus"
	CustomButton.className = "btn btn-default btn-block"

	CustomButton.onclick = function(){
		addCustomForm(tablediv)
	}

	CustomButton.appendChild(t)
	CustomButton.id = "CustomButton"
	tablediv.appendChild(CustomButton)
}

custom_id = 2000
function add_custom_item(){
	var id = custom_id.toString()
	custom_id += 1
	var cat = "Extras"
	var item = $("#type").val()
	var subitem = $("#subtype").val()
	var price = $("#price").val()
	if(price){
		if (price.charAt(0) == '£'){
			price = price.substr(1)
		}
	}
	price = parseFloat(price)
	var turnaround = $("#turnaround").val()
	var pricemin = 0
	var amount = 1

	item_added(id, cat, item, subitem, price, pricemin, turnaround, amount) 
	$("#newItem").attr("hidden", true)
	return false
}

function addCustomForm(tablediv){
	$("#newItem").attr("hidden", false)
}

function add_order_button(tablediv){
	// tablediv.appendChild(document.createElement("br"))
	// var OrderButton = document.createElement("button");
	// var t = document.createTextNode("Submit Order")
	// var OrderButtonIcon = document.createElement("span")
	// OrderButtonIcon.className = "glyphicon glyphicon-play"
	// OrderButton.className = "btn btn-default btn-primary btn-lg btn-block"
	// OrderButton.onclick = submit_order()

	// function(){
	// 	window.sessionStorage.setItem("cart", JSON.stringify(cart)); // Saving
	// 	// verify
		// send using AJAX


		// document.getElementById("hiddenform").submit()
		// var cart2 = sessionStorage.getItem( "cart" );
		// $("#test").text(cart2)
	// }
	// OrderButton.appendChild(t)
	// OrderButton.id = "OrderButton"
	// tablediv.appendChild(OrderButton)
	// tablediv.appendChild(document.createElement("br"))
}

function add_total_to_title(){
	if(runningtotal != 0){
		string = ":\xA0" + formattedtotal
		$('#order_amount').text(string)
	}
	else
		$('#order_amount').text("")
}

function create_item_row(i){
	var tr=document.createElement('tr');
	var td=document.createElement('td');
	td.appendChild(document.createTextNode(cart[i][2]))
	if(cart[i][3]){
		td.appendChild(document.createTextNode(" ("))
		td.appendChild(document.createTextNode(cart[i][3]))
		td.appendChild(document.createTextNode(")"))
	}
	if (cart[i][6] != 1){
		var qtytext = " x" + cart[i][6]
		td.appendChild(document.createTextNode(qtytext))
	}

	td.id = 'ordertable_name'
	tr.appendChild(td);

	var td=document.createElement('td')
	td.id = "paddedcell"
	td.appendChild(document.createTextNode("£"))
	var priceparsed = document.createTextNode(cart[i][4])
	td.appendChild(priceparsed)
	td.id = 'ordertable_unitprice'
	if (cart[i][6] != 1){
		var qtytext = " each"
		td.appendChild(document.createTextNode(qtytext))
	}
	tr.appendChild(td);

	var td=document.createElement('td');
	var addbutton = document.createElement("button");
	addbutton.className = "btn btn-default btn-xs"
	addbutton.ID = "A" + cart[i][0]
	addbutton.onclick = function(){
		change_quantity_by_id(this.ID.substring(1), 1)
	}

	var addbuttonicon = document.createElement("i")
	addbuttonicon.className = "glyphicon glyphicon-plus"
	addbutton.appendChild(addbuttonicon);
	td.appendChild(addbutton);
	tr.appendChild(td);

	var td=document.createElement('td');
	var removebutton = document.createElement("button");
	removebutton.className = "btn btn-default btn-xs"
	removebutton.ID = "B" + cart[i][0]
	removebutton.onclick = function(){
		change_quantity_by_id(this.ID.substring(1), -1)
	}

	var removebuttonicon = document.createElement("i")
	removebuttonicon.className = "glyphicon glyphicon-minus"
	removebutton.appendChild(removebuttonicon);
	td.appendChild(removebutton);
	tr.appendChild(td);
	
	return tr
}

function create_total_row(){
	var th=document.createElement('th');
		var td=document.createElement('td');
		totalstring = document.createTextNode("Total\u00a0")
		td.appendChild(totalstring) // + runningtotal)
		
		var td2=document.createElement('td');
		string = document.createTextNode(formattedtotal)
		td2.appendChild(string)
		if (runningtotal != 0){
			th.appendChild(td);
			th.appendChild(td2);
		}
	return th
}

function submit_order(){
	bootbox.confirm("Are you sure you want to submit this?", function(result) {
 	if(result){

		var escaped_cart = []
 	 	for (var i=0; i<cart.length; i++){
 	 		escaped_cart[i] = $.map(cart[i], function(n){
 	 			return escape(n)
 	 		})
 	 	}

 	 	json_string = JSON.stringify(escaped_cart)
 	 	console.log(json_string)
 	 	var ordernumber = $("#ordernumber").val()

 	 	post('/partner/submitorder', {
 	 		json: json_string,
 	 		ordernumber: ordernumber
 	 	})

 	 }
	}); 
}

function post(path, params, method) {
    method = method || "post"; // Set method to post by default if not specified.

    // The rest of this code assumes you are not using a library.
    // It can be made less wordy if you use one.
    var form = document.createElement("form");
    form.setAttribute("method", method);
    form.setAttribute("action", path);

    for(var key in params) {
        if(params.hasOwnProperty(key)) {
            var hiddenField = document.createElement("input");
            hiddenField.setAttribute("type", "hidden");
            hiddenField.setAttribute("name", key);
            hiddenField.setAttribute("value", params[key]);

            form.appendChild(hiddenField);
         }
    }

    document.body.appendChild(form);
    form.submit();
}