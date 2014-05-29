from google.appengine.ext import ndb
from google.appengine.api import images

DEFAULT_PARTNER_NAME = 'default_name'
DEFAULT_PARTNER_OUTCODES = 'default_outcode'
DEFAULT_ORDER_ID = 'default_name'
DEFAULT_PARTNER_KEY = 'default_partner_key'

def partner_key(partner_name=DEFAULT_PARTNER_NAME):
	return ndb.Key('Partner', partner_name)

def order_key(partner_name=DEFAULT_PARTNER_NAME):
	return ndb.Key('Partner', partner_name)

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
	email = ndb.StringProperty()


	start_day = ndb.IntegerProperty() # Sunday = 0, Saturday = 6
	end_day = ndb.IntegerProperty()

	start_hr = ndb.IntegerProperty()
	start_min = ndb.IntegerProperty()
	end_hr = ndb.IntegerProperty()
	end_min = ndb.IntegerProperty()
	window_size = ndb.IntegerProperty()
	start_day = ndb.IntegerProperty()
	end_day = ndb.IntegerProperty()

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
		possible_days = []
		i = self.start_day
		while i <= self.end_day:
			j = i # Won't let us use 'i' in append for some silly reason
			possible_days.append(j)
			i = i+1

		
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
		print "SENT TXT TO CLEANER"

	def send_email_to_cleaner(self):

		print "SENT EMAIL TO CLEANER"

		partner = partner_key(service_partner).get()

		from google.appengine.api import mail

		message = mail.EmailMessage(
			sender="60 Second Laundry <orders@60secondlaundry.com>",
		    subject="Order Receipt")

		to_string = first_name + " " + last_name + " <" + email + ">"
		message.to = to_string
		message.body = "Dear " + first_name + """:

		Thanks for your order.

		If you have any questions about your order, contact your cleaner directly on:
		""" + partner.phonenumber + """

		Here are the details you need to keep.

		If you enjoyed our service, please let us know via will.taylor@60secondlaundry.com

		The 60 Second Laundry Team
		"""

		message.send()

	def send_email_to_customer(self):
		print "SENT EMAIL TO CUSTOMER"

		from google.appengine.api import mail

		message = mail.EmailMessage(
			sender="60 Second Laundry <orders@60secondlaundry.com>",
		    subject="Order Receipt")

		message.to = "Will Taylor <wrftaylor@gmail.com>"
		message.body = """
		Dear Will:

		Thanks for your order.

		If you have any questions about your order, contact your cleaner directly on:
		07772622352

		Here are the details you need to keep.

		If you enjoyed our service, please let us know via will.taylor@60secondlaundry.com

		The 60 Second Laundry Team
		"""

		message.send()

class postcode_attempt(ndb.Model):
	postcode = ndb.StringProperty()
	time = ndb.DateTimeProperty(auto_now_add=True)


class feedback(ndb.Model):
	feedback = ndb.StringProperty()
	page = ndb.StringProperty()
	time = ndb.DateTimeProperty(auto_now_add=True)


