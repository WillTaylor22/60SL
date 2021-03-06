import jinja2

import model
from string import split
import csv # for reading the csv
import quopri # for "= every 75 char" bug

from google.appengine.ext import ndb

import os.path
import webapp2

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers 

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

""" methods """
def grab(partner_name, fname):
  #This section grabs the data
  
  __location__ = os.path.realpath(
      os.path.join(os.getcwd(), os.path.dirname(__file__)))
  fpath = os.path.join(__location__, "menus", fname)
  # you now have a filepath that you can open the file with

  #open the file, the opened file is called importfile
  with open(fpath, 'rU') as importfile:
    dataimport = csv.reader(importfile, quotechar='"')
    # dataimport then reads opened file

    # for each row opened, print a comma, then the row.
    for row in dataimport:
      # adds entry
      print "New Entry -------"
      print partner_name
      myItem = model.menuitem(parent=model.partner_key(partner_name))
      print "loading: " + row[0]
      myItem.itemid = int(row[0])     
      print "loading: " + row[1]
      myItem.tabname = row[1]
      print "loading: " + row[2]
      myItem.item = row[2]
      print "loading: " + row[3]
      myItem.subitem = row[3]
      print "loading price: ", row[4]
      if (row[4] == ""):
        row[4] = 0
      print "loading price: ", row[4]
      myItem.price = float(row[4])
      print "loading: ", row[5]
      if (row[5] == ""):
        row[5] = 0
      print "reloading from pricemin: ", row[5]
      myItem.pricemin = float(row[5])
      print "loading: ", row[6]
      if (row[6] == ""):
        row[6] = 0
      print "reloading from pricemax: ", row[6]
      myItem.pricemax = float(row[6])
      print "loading: ", row[7]
      myItem.time = row[7]
      myItem.put()

      # prints to screen
      print row
  print 'DONE'

def clear_items(partner_name):
  print "IN CLEAR_ITEMS"
  query = model.menuitem.query(ancestor=model.partner_key(partner_name))
  partners = query.fetch(keys_only=True)
  ndb.delete_multi(partners)

""" admin handlers """

class InputHandler(webapp2.RequestHandler):
  def get(self): # this page is ONLY for input of partners
    upload_url = blobstore.create_upload_url('/upload')

    template_values ={
      'upload_url': upload_url
    }

    template = JINJA_ENVIRONMENT.get_template('templates/admin/add.html')
    self.response.write(template.render(template_values))

class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
  # This view takes the input, populates a new model and adds to DB
  def post(self): 
    ## Get the POST data and put it into variables
    # Blob data: ('logo' is file upload field in the form)
    upload_files = self.get_uploads('logo')
    blob_info = upload_files[0]
    blob_key = blob_info.key()

    partner_name = self.request.get('name')
    # Create a new "Partner" with a new partner key
    partner = model.Partner(parent=model.partner_key(partner_name))

    
    partner_outcodes = self.request.get('outcodes')
    partner_outcodes = quopri.decodestring(partner_outcodes)
    partner_outcodes = partner_outcodes.split()
    partner_address = self.request.get('address')
    partner_minimum_order = self.request.get('minimum_order')
    partner_delivery_cost = self.request.get('delivery_cost')

    partner.phonenumber = self.request.get('phonenumber')
    partner.phonenumber_2 = self.request.get('phonenumber_2')
    partner.email = self.request.get('email')
    partner.email_2 = self.request.get('email_2')
    partner.email_3 = self.request.get('email_3')

    
    # Give the new partner our data
    partner.name = partner_name
    partner.address = partner_address
    partner.outcodes = partner_outcodes
    partner.minimum_order = int(partner_minimum_order)
    partner.delivery_cost = partner_delivery_cost

    fname = self.request.get('filename')

    partner.start_hr = int(self.request.get('start_hr'))
    partner.start_min = int(self.request.get('start_min'))
    partner.end_hr = int(self.request.get('end_hr'))
    partner.end_min = int(self.request.get('end_min'))
    partner.window_size = int(self.request.get('window_size'))

    partner.last_orders_hr = int(self.request.get('last_orders_hr'))
    partner.last_orders_min = int(self.request.get('last_orders_min'))
    partner.end_of_morning_hr = int(self.request.get('end_of_morning_hr'))
    partner.end_of_morning_min = int(self.request.get('end_of_morning_min'))

    partner.last_orders_same_day_hr = int(self.request.get('last_orders_same_day_hr'))
    partner.last_orders_same_day_min = int(self.request.get('last_orders_same_day_min'))

    partner.shirts = self.request.get('shirts')
    partner.suits = self.request.get('suits')



    days = self.request.get('days')
    day_list = days.split()
    day_list = map(int, day_list)
    partner.days = day_list

    # OLD:
    # partner.start_day = int(self.request.get('start_day'))
    # partner.end_day = int(self.request.get('end_day'))


    partner.logo_key = blob_key # n.b. blobstore.BlobReferenceProperty() takes a blob_info
    
    partner.populate_slots()

    # Use to clear all items
    clear_items(partner_name) 

    # Populate if no items exist
    if fname:
      grab(partner_name, fname)



    partner.put()

    # redirect
    self.redirect('/viewpartners')

class ServeHandler(blobstore_handlers.BlobstoreDownloadHandler):
  def get(self):
    #search query, for displaying partners
    partner_query = model.Partner.query()
    partners = partner_query.fetch(50)

    template_values ={
      'partners': partners,
    }

    template = JINJA_ENVIRONMENT.get_template('templates/admin/viewpartners.html')
    self.response.write(template.render(template_values))

class DeleteHandler(webapp2.RequestHandler):
  def post(self): # this page is ONLY for input of partners
    partner_name = self.request.get('partner_name')

    q = model.Partner.query(model.Partner.name == partner_name)
    results = q.fetch(10)
    
    for result in results:
      result.key.delete()

    self.redirect('/viewpartners')        

""" allows you to manually re-add a menu to a cleaner """
class MenuHandler(webapp2.RequestHandler):
  def get(self):
    template_values ={
    }

    template = JINJA_ENVIRONMENT.get_template('templates/admin/addmenu.html')
    self.response.write(template.render(template_values))

  def post(self):
    partner_name = self.request.get('partner_name')
    fname = self.request.get('filename')
    
    clear_items(partner_name)

    grab(partner_name, fname)

    template_values ={
    }

    template = JINJA_ENVIRONMENT.get_template('templates/admin/addmenu.html')
    self.response.write(template.render(template_values))


""" allows you to manually add bestsellers to a cleaner """
class AddShirtsHandler(webapp2.RequestHandler):
  def get(self):
    template_values ={
    }

    template = JINJA_ENVIRONMENT.get_template('templates/admin/addshirts.html')
    self.response.write(template.render(template_values))

  def post(self):
    partner_name = self.request.get('partner_name')
    shirts = self.request.get('shirts')
    suits = self.request.get('suits')
    
    partner = model.get_partner(partner_name)

    partner.shirts = shirts
    partner.suits = suits
    partner.put()

    success = True

    template_values ={
      success: success
    }

    template = JINJA_ENVIRONMENT.get_template('templates/admin/addshirts.html')
    self.response.write(template.render(template_values))

