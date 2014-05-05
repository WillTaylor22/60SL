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

	@property
	def logo_url(self):
		return images.get_serving_url(self.logo_key)

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


class postcode_attempt(ndb.Model):
	postcode = ndb.StringProperty()
	time = ndb.DateTimeProperty(auto_now_add=True)