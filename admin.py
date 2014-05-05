import os
import urllib
import webapp2
import jinja2
import mymodels
from string import split
from google.appengine.ext import ndb

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

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
		partner_outcodes = self.request.get('outcodes')
		partner_outcodes = partner_outcodes.split()
		partner_minimum_order = self.request.get('minimum_order')
		partner_delivery_cost = self.request.get('delivery_cost')

		# Create a new "Partner" with a new partner key
		partner = mymodels.Partner(parent=mymodels.partner_key(partner_name))

		# Give the new partner our data
		partner.name = partner_name
		partner.outcodes = partner_outcodes
		partner.minimum_order = int(partner_minimum_order)
		partner.delivery_cost = partner_delivery_cost
		
		partner.logo_key = blob_key # n.b. blobstore.BlobReferenceProperty() takes a blob_info
		partner.put()

		# redirect
		self.redirect('/viewpartners')

class ServeHandler(blobstore_handlers.BlobstoreDownloadHandler):
	def get(self):
		#search query, for displaying partners
		partner_query = mymodels.Partner.query()
		partners = partner_query.fetch(50)

		template_values ={
			'partners': partners,
		}

		template = JINJA_ENVIRONMENT.get_template('templates/admin/viewpartners.html')
		self.response.write(template.render(template_values))

class DeleteHandler(webapp2.RequestHandler):
	def post(self): # this page is ONLY for input of partners
		partner_name = self.request.get('name')

		q = mymodels.Partner.query(mymodels.Partner.name == partner_name)
		print partner_name
		results = q.fetch(10)
		print results
		
		for result in results:
			result.key.delete()

		self.redirect('/viewpartners')	    	

