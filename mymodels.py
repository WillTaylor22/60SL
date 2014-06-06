from google.appengine.ext import ndb
from google.appengine.api import images
import string
from google.appengine.api import mail


DEFAULT_PARTNER_NAME = 'default_name'
DEFAULT_PARTNER_OUTCODES = 'default_outcode'
DEFAULT_ORDER_ID = 'default_name'
DEFAULT_PARTNER_KEY = 'default_partner_key'

def partner_key(partner_name=DEFAULT_PARTNER_NAME):
	return ndb.Key('Partner', partner_name)

def order_key(partner_name=DEFAULT_PARTNER_NAME):
	return ndb.Key('Partner', partner_name)

def get_partner(partner_name):
	query = Partner.query(Partner.name == partner_name)
	return query.fetch(1)[0]

#models
class Partner(ndb.Model):
	# Models an individual partner entry with name and outcodes
	name = ndb.StringProperty()
	address = ndb.StringProperty()
	outcodes = ndb.StringProperty(repeated=True)
	logo_key = ndb.BlobKeyProperty() #stores the key for the image
	minimum_order = ndb.IntegerProperty()
	delivery_cost = ndb.StringProperty()

	phonenumber = ndb.StringProperty()
	phonenumber_2 = ndb.StringProperty()
	email = ndb.StringProperty()
	email_2 = ndb.StringProperty()
	email_3 = ndb.StringProperty()

	# Out of date
	start_day = ndb.IntegerProperty() # Sunday = 0, Saturday = 6
	end_day = ndb.IntegerProperty()
	##

	days = ndb.IntegerProperty(repeated=True)

	start_hr = ndb.IntegerProperty()
	start_min = ndb.IntegerProperty()
	end_hr = ndb.IntegerProperty()
	end_min = ndb.IntegerProperty()
	window_size = ndb.IntegerProperty()
	start_day = ndb.IntegerProperty()
	end_day = ndb.IntegerProperty()

	last_orders_hr = ndb.IntegerProperty()
	last_orders_min = ndb.IntegerProperty()
	end_of_morning_hr = ndb.IntegerProperty()
	end_of_morning_min = ndb.IntegerProperty()

	delivery_slots = ndb.StringProperty(repeated=True)

	@property
	def logo_url(self):
		return images.get_serving_url(self.logo_key)


	# 1. Populate array of values
	# Given: Start time, end time, window size
	# Create a slot start every 15 minutes from start time to (end time - window)
	# Create a label for each slot start

	# 2. put array into template_values
	# 3. display template values currectly in the app

	def populate_slots(self):
		last_delivery = 0
		slot = 0
		delivery_slot = ''

		last_delivery = self.end_hr*60 + self.end_min - self.window_size
		slot = self.start_hr*60 + self.start_min
		print "slot: ", slot
		print "last_delivery: ", last_delivery

		while slot <= last_delivery:
			print "NEW SLOT ---"
			print "slot: ", slot

			# This just gives you a double zero where required
			first_mins = str(slot%60)
			if first_mins == '0':
				first_mins = '00'
			last_mins = str((slot+self.window_size)%60)
			if last_mins == '0':
				last_mins = '00'

			# This gives you a 0 ahead of single digit hours for 24hr time, e.g. 07:00
			first_hour = str(slot/60)
			if len(first_hour) == 1:
				first_hour = '0' + first_hour
			last_hour = str((slot+self.window_size)/60)
			if len(last_hour) == 1:
				last_hour = '0' + last_hour

			delivery_slot = first_hour + ':' + first_mins # + \
				#" - " + last_hour + ':' + last_mins
			print "delivery_slot: ", delivery_slot
			self.delivery_slots.append(delivery_slot)
			slot += 15

		print self.delivery_slots

	def get_next_three_days(self):  # Gets an array containing next 3 possible days as dates
		print "IN NEXT THREE DAYS"

		# Logic:
		# aiming to create an array [1, 2, 3] that contains the next three dates
		# but skips a date if there is no delivery on that day
		# which means it does a check on the day of week of that date


		# Creates possible_days e.g. [1, 2, 3, 4, 5]
		possible_days = self.days
		print "possible_days: ", possible_days
		# OLD WAY:
		# i = self.start_day
		# while i <= self.end_day:
		# 	j = i # Won't let us use 'i' in append for some silly reason
		# 	possible_days.append(j)
		# 	i = i+1

		
		from datetime import date, timedelta

		today = date.today()
		trial_date = ''
		next_three_days = []
		i = 0 # i itterates over days
		j= 0
		while i < 7:
			trial_date = today + timedelta(i)

			if (trial_date.isoweekday()%7 in possible_days) :
				next_three_days.append(trial_date)
				j += 1

			if j == 3:
				break
			i += 1

		print "next_three_days: ", next_three_days
		
		
		return next_three_days

class menuitem(ndb.Model):
	# an individual entry in the database
	itemid = ndb.IntegerProperty()
	tabname = ndb.StringProperty()
	item = ndb.StringProperty()
	subitem = ndb.StringProperty()
	price = ndb.FloatProperty()
	pricemin = ndb.FloatProperty()
	pricemax = ndb.FloatProperty()
	time = ndb.StringProperty()


import urllib
from google.appengine.api import urlfetch

def send_sms(username, password, to, message, originator):
	requested_url = 'http://api.textmarketer.co.uk/gateway/?option=xml' +\
	                "&username=" + username + "&password=" + password +\
	                "&to=" + to + "&message=" + urllib.quote(message) +\
	                "&orig=" + urllib.quote(originator)

	result = urlfetch.fetch(requested_url)
	return result.content

class order(ndb.Model):
	# an individual order
	ordertime = ndb.DateTimeProperty(auto_now_add=True)

	first_name = ndb.StringProperty()
	last_name = ndb.StringProperty()
	address1 = ndb.StringProperty()
	address2 = ndb.StringProperty()
	address3 = ndb.StringProperty()
	postcode = ndb.StringProperty()
	collectioninstructions = ndb.StringProperty()
	phonenumber = ndb.StringProperty()
	email = ndb.StringProperty()
	collection_time_date = ndb.StringProperty()
	delivery_time_date = ndb.StringProperty()
	service_partner = ndb.StringProperty()
	submitted = ndb.BooleanProperty(default=False)

	@property 
	def ordernumber(self):
		return self.key.id()

	def send_txt_to_cleaner(self):
		partner = get_partner(self.service_partner)

		self.send_cleaner_order_txt(partner.phonenumber)
		
		if partner.phonenumber_2:
			self.send_cleaner_order_txt(partner.phonenumber_2)
		
	def send_cleaner_order_txt(self, partner_phonenumber):
		username = '853av'
		password = '552cu'
		to = partner_phonenumber
		originator = '60SeLaundry'
		
		# [NEW ORDER] Will Taylor, 17 Corsham Street N1 6DR, Friday 30th May 14:00 - 15:00
		message = '[NEW ORDER] '+self.first_name+' '+self.last_name+', '+self.address1
		try:
		    address2
		except NameError:
		    address2 = None
		if address2:
			message = message + ', ' + self.address2
		message = message + ', ' + self.postcode
		message = message + ', ' + self.collection_time_date
		message = message + ' -> ' + self.delivery_time_date
		
		if len(message) > 150:
			message = '[NEW ORDER] '+self.first_name+' '+self.last_name+', '+self.address1
			message = message + ', ' + self.postcode
			message = message + ', ' + self.collection_time_date
			message = message + ' -> ' + self.delivery_time_date

		if len(message) > 150:
			message = '[NEW ORDER] '+self.first_name+' '+self.last_name+', '+self.address1
			message = message + ', ' + self.postcode
			message = message + ', ' + self.collection_time_date

		if len(message) > 150:
			message = '[NEW ORDER] '+self.collection_time_date
			message = message + ', See Email For Details'

		result = send_sms(username, password, to, message, originator)
		print "TXT RESPONSE: ", result


	def send_email_to_cleaner(self):

		partner = get_partner(self.service_partner)

		self.send_cleaner_email(partner.name, partner.email)

		if partner.email_2:
			self.send_cleaner_email(partner.name, partner.email_2)

		if partner.email_3:
			self.send_cleaner_email(partner.name, partner.email_3)

	def send_cleaner_email(self, partner_name, partner_email):

		sender_string = "60 Second Laundry <orders@60secondlaundry.com>"

		# E.g. New Order: Will Taylor @ 29th May 17:00 - 18:00
		subject_string = "New Order: " + self.first_name + " " + self.last_name \
		+ " @ " + self.collection_time_date
		
		to_string = partner_name + " <" + partner_email + ">"
		body_string = "Dear " + partner_name + """:

		You have received an order!

		For ALL questions & issues with the order, contact your customer directly on:
		""" + self.phonenumber + """

		Order details:
		Customer Name: """ + self.first_name + " " + self.last_name + """
		Address: """ + self.address1 + """
		""" + self.address2 + """
		""" + self.address3 + """
		""" + self.postcode + """
		Order Instructions: """ + self.collectioninstructions + """
		Customer Phone Number: """ + self.phonenumber + """
		Customer Email: """ + self.email + """

		Collection Time: """ + self.collection_time_date + """
		Delivery Time: """ + self.delivery_time_date + """
		(We recommend that you call 30 mins in advance of arrival to let them know you are coming and avoid any missed deliveries)

		Any questions about 60 Second Laundry, contact Will on will.taylor@60secondlaundry or call him on 07772622352.

		If you enjoyed our service, please let us know via will.taylor@60secondlaundry.com

		The 60 Second Laundry Team
		We love cleaners!
		"""

		message = mail.EmailMessage(
			sender=sender_string,
		    subject=subject_string)

		message.to = to_string
		message.body = body_string

		message.send()

	def send_email_to_customer(self):
		print "SENT EMAIL TO CUSTOMER"

		partner = get_partner(self.service_partner)

		from google.appengine.api import mail

		message = mail.EmailMessage(
			sender="60 Second Laundry <orders@60secondlaundry.com>",
		    subject="Receipt For Your Order On " + self.collection_time_date)

		message.to = self.first_name + " " + self.last_name + " <" + self.email + ">"
		message.body = """
		Dear Will:

		Thank you for your order!

		If you have any questions or changes with your order, contact your cleaner directly on:
		""" + partner.phonenumber + """

		Order details:
		Your Name: """ + self.first_name + " " + self.last_name + """
		Address: """ + self.address1 + """
		""" + self.address2 + """
		""" + self.address3 + """
		""" + self.postcode + """
		Order Instructions: """ + self.collectioninstructions + """
		Customer Phone Number: """ + self.phonenumber + """
		Customer Email: """ + self.email + """

		Collection Time: """ + self.collection_time_date + """
		Delivery Time: """ + self.delivery_time_date + """
		(We do ask cleaners to call 30 mins in advance of arrival to let you know they are coming)


		If you enjoyed our service, please email Will on will.taylor@60secondlaundry.com

		The 60 Second Laundry Team
		We Love Cleaners!
		"""

		message.send()

class postcode_attempt(ndb.Model):
	postcode = ndb.StringProperty()
	time = ndb.DateTimeProperty(auto_now_add=True)


class feedback(ndb.Model):
	feedback = ndb.StringProperty()
	page = ndb.StringProperty()
	time = ndb.DateTimeProperty(auto_now_add=True)


