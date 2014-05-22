from google.appengine.ext import ndb
from google.appengine.api import images

DEFAULT_PARTNER_NAME = 'default_name'
DEFAULT_PARTNER_OUTCODES = 'default_outcode'
DEFAULT_ORDER_ID = 'default_name'

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

	def get_next_three_days(self):  # Gets an array containing next 3 possible days

		# Creates possible_days ~ e.g. [1, 2, 3, 4, 5]
		# TESTING print "self.start_day: ", self.start_day
		possible_days = []
		# print possible_days
		i = self.start_day
		while i <= self.end_day:
			j = i # Won't let us use 'i' for some silly reason
			possible_days.append(j)
			i = i+1

		#p rint possible_days


		import time

		today_day = int(time.strftime("%w"))
		print "possible_days: ", possible_days
		print "today_day: ", today_day
		try:
			today_index = possible_days.index(today_day)
		except ValueError:
			today_index = -1
		print "today_index: ", today_index
		next_three_days = ['TEST','TEST','TEST']

		# Series of if statements that allow the next_three_days array to 
		# populate with the next 3 available days, rolling over if we go over
		# the top of the "days available" amount

		if today_index == -1: # Today is weekend, populate with start of next week
			next_three_days[0] = possible_days[0]
			next_three_days[1] = possible_days[1]
			next_three_days[2] = possible_days[2]
		else: # Today is weekday, populate with day number of today
			next_three_days[0] = possible_days[today_index]
			# Check if tomorrow is in possible_days array
			if today_index + 1 < len(possible_days): # Tomorrow is within possible_days loop, populate with next index
				next_three_days[1] = possible_days[today_index + 1]
				if today_index + 2 < len(possible_days): # Day after tomorrow is in loop, populate with day after tomorrow
					next_three_days[2] = possible_days[today_index + 2]
				else: # Day after tomorrow is not in loop, populate with start of next week
					next_three_days[2] = possible_days[0]
			# tomorrow is not in possible_days array 
			else: # populate with start of the next week
				next_three_days[1] = possible_days[0]
				next_three_days[2] = possible_days[1]


		# Turns numbers to strings that say Today, Tomorrow or the day.
		i = 0
		while i<3:
			if next_three_days[i] == today_day:
				next_three_days[i]= 'Today'
			elif next_three_days[i] == (today_day + 1) % 7: # % bit for "7 == 0" logic
				next_three_days[i]= 'Tomorrow'
			elif next_three_days[i]==1:
				next_three_days[i]= 'Monday'
			elif next_three_days[i]==2:
				next_three_days[i]= 'Tuesday'
			elif next_three_days[i]==3:
				next_three_days[i]= 'Wednesday'
			elif next_three_days[i]==4:
				next_three_days[i]= 'Thursday'
			elif next_three_days[i]==5:
				next_three_days[i]= 'Friday'
			elif next_three_days[i]==6:
				next_three_days[i]= 'Saturday'
			elif next_three_days[i]==0:
				next_three_days[i]= 'Sunday'
			i += 1
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
		pass

	def send_email_to_cleaner(self):
		#get cleaner


		from google.appengine.api import mail

		message = mail.EmailMessage(
			sender="Example.com Support <support@example.com>",
		    subject="Your account has been approved")

		message.to = "Will Taylor <wrftaylor@gmail.com>"
		message.body = """
		Dear Will:

		Your example.com account has been approved.  You can now visit
		http://www.example.com/ and sign in using your Google Account to
		access new features.

		Please let us know if you have any questions.

		The example.com Team
		"""

		message.send()

	def send_email_to_customer(self):
		pass

class postcode_attempt(ndb.Model):
	postcode = ndb.StringProperty()
	time = ndb.DateTimeProperty(auto_now_add=True)


class feedback(ndb.Model):
	feedback = ndb.StringProperty()
	page = ndb.StringProperty()
	time = ndb.DateTimeProperty(auto_now_add=True)


