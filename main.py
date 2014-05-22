# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import urllib
import webapp2
import jinja2
from datetime import datetime
import csv # for reading the csv
import cgi

from gaesessions import get_current_session


# store partner_key
# store order_key


import mymodels
from google.appengine.ext import ndb
from bin import postcode

# from admin import InputHandler, UploadHandler, ServeHandler, DeleteHandler

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

def datetimeformat(value, format='%H:%M / %d-%m-%Y'):
    return value.strftime(format)

def currencyformat(value):
	if(value % 1 == 0):
		result = "£{:,.0f}".format(value)
	else:
		result = "£{:,.2f}".format(value)
	result = result.decode("utf8")
	return result


JINJA_ENVIRONMENT.filters['datetimeformat'] = datetimeformat
JINJA_ENVIRONMENT.filters['currencyformat'] = currencyformat



def grab():
	#This section grabs the data
	fname = "WashingtonExport.csv"
	partner_name = "Washington Dry Cleaners"

	__location__ = os.path.realpath(
	    os.path.join(os.getcwd(), os.path.dirname(__file__)))
	fpath = os.path.join(__location__, fname)
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
			myItem = mymodels.menuitem(parent=mymodels.partner_key(partner_name))
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

# Handlers (Views)
class MainHandler(webapp2.RequestHandler):
	def get(self):
		template_values = {}

		template = JINJA_ENVIRONMENT.get_template('templates/index.html')
		self.response.write(template.render(template_values))

class ListingsHandler(webapp2.RequestHandler):
	def get(self):

		mypostcode = self.request.get('postcode')

		# record for analytics
		postcodeattempt = mymodels.postcode_attempt()
		postcodeattempt.postcode = mypostcode
		postcodeattempt.put()

		outcode = ''

		# create cookie to store "postcode"
		session = get_current_session()
		session['postcode'] = mypostcode

		try:
			outcode = postcode.parse_uk_postcode(mypostcode)[0]

			query = mymodels.Partner.query(mymodels.Partner.outcodes == outcode)
			partners = query.fetch(10)


			if partners[0]:
				template_values = {
					'postcode' : mypostcode,
					'partners' : partners
				}
				template = JINJA_ENVIRONMENT.get_template('templates/listings.html')

		except IndexError:
			errormessage = "No supplier at this postcode. We've noted your postcode (" + mypostcode +") and will look for a cleaner near you!"
			template_values = {
				'error_message': errormessage
			}
			template = JINJA_ENVIRONMENT.get_template('templates/index.html')
		except ValueError:
			errormessage = "Postcode not recognised"
			template_values = {
				'error_message': errormessage
			}
			template = JINJA_ENVIRONMENT.get_template('templates/index.html')
		
		self.response.write(template.render(template_values))


class MenuHandler(webapp2.RequestHandler):
	def get(self):
		partner_name = self.request.get('partner_name')
		postcode = 'Postcode'

		session = get_current_session()
		session['partner'] = partner_name

		query = mymodels.Partner.query(mymodels.Partner.name == partner_name)
		partner = query.fetch(1)[0]

		if session.has_key('postcode'):
			postcode = session['postcode']


		query = mymodels.menuitem.query(
			ancestor=mymodels.partner_key(partner_name)).order(ndb.GenericProperty("itemid"))
		menuitems = query.fetch(300)

		# Populate if no items exisit
		if(menuitems):
			pass
		else:
			grab()
			menuitems = query.fetch(300)

		template_values = {
			'postcode': postcode,
			'partner' : partner,
			'menuitems' : menuitems
		}

		template = JINJA_ENVIRONMENT.get_template('templates/menu.html')
		self.response.write(template.render(template_values))

class FormHandler(webapp2.RequestHandler):
	def get(self):

		partner_name = self.request.get('partner_name')

		session = get_current_session()
		postcode = ''
		partner = ''

		if session.has_key('postcode'):
			postcode = session['postcode']

		if session.has_key('partner'):
			partner = session['partner']

		query = mymodels.Partner.query(mymodels.Partner.name == partner_name)
		partner = query.fetch(1)[0]

		next_three_days = partner.get_next_three_days()
		print next_three_days
		# 1. Populate array of values
		# Given: Start time, end time, window size
		# Create a slot start every 15 minutes from start time to (end time - window)
		# Create a label for each slot start


		# 2. put array into template_values
		# 3. display template values currectly in the app

		template_values = {
			'next_three_days': next_three_days,
			"partner_name" : partner_name,
			"postcode": postcode,
			'partner': partner,
		}
		template = JINJA_ENVIRONMENT.get_template('templates/form.html')
		self.response.write(template.render(template_values))

class ReviewOrderHandler(webapp2.RequestHandler):
	# Receives info from Collection(form)
	# then sends user to review the order
	def post(self):

		#creates new order and associates it with the partner
		partner_name = self.request.get('partner_name')

		partner_k = mymodels.partner_key(partner_name)
		myOrder = mymodels.order(parent=partner_k)

		# get order info and load it into a model
		myOrder.first_name = self.request.get('first_name')
		myOrder.last_name = self.request.get('last_name')
		myOrder.address1 = self.request.get('Address_line_1')
		myOrder.address2 = self.request.get('Address_line_2')
		myOrder.address3 = self.request.get('Address_line_3')
		myOrder.postcode = self.request.get('Postcode')
		myOrder.collectioninstructions = self.request.get('Collect_instructions')
		myOrder.phonenumber = self.request.get('Phone_number')
		myOrder.email = self.request.get('Email')
		myOrder.collection_time_date = self.request.get('collection_day_output') + ', ' + self.request.get('collection_time_output')
		myOrder.delivery_time_date = self.request.get('delivery_day_output') + ', ' + self.request.get('delivery_time_output')
		myOrder.service_partner = partner_name

		myOrder.put()

		session = get_current_session()
		session['ordernumber'] = myOrder.key.id()
		session['partnername'] = partner_name

		template_values = {
			"order" : myOrder,
			"partner_name" : partner_name
		}
		template = JINJA_ENVIRONMENT.get_template('templates/review.html')
		self.response.write(template.render(template_values))

class SubmitHandler(webapp2.RequestHandler):
	# The order has been created and 
	def post(self):

		session = get_current_session()
		ordernumber = session['ordernumber']
		partnername = session['partnername']

		myOrder_k = ndb.Key('Partner', partnername, 'order', ordernumber)
		myOrder = myOrder_k.get()

		if myOrder:
			myOrder.submitted = True
			myOrder.put()

		myOrder.send_txt_to_cleaner()
		myOrder.send_email_to_cleaner()
		myOrder.send_email_to_customer()

		template_values = {
			"order" : myOrder,
		}

		# debugging:
		# template = JINJA_ENVIRONMENT.get_template('templates/review.html')

		template = JINJA_ENVIRONMENT.get_template('templates/thankyou.html')
		self.response.write(template.render(template_values))

class CleanerLoginHandler(webapp2.RequestHandler):
	def get(self):
		template_values = {}
		template = JINJA_ENVIRONMENT.get_template('templates/cleanerlogin.html')
		self.response.write(template.render(template_values))


class FeedbackHandler(webapp2.RequestHandler):
	def post(self):
		myFeedback = mymodels.feedback()
		myFeedback.page = self.request.get('feedback_page')
		myFeedback.feedback = self.request.get('feedback_content')
		myFeedback.put()


class TestHandler(webapp2.RequestHandler):
	def get(self):
		template_values = {}
		template = JINJA_ENVIRONMENT.get_template('templates/test.html')
		self.response.write(template.render(template_values))

# URL Routing happens here
app = webapp2.WSGIApplication([
    ('/', MainHandler),
    webapp2.Route('/near', handler=ListingsHandler, name='near'),
	#    webapp2.Route('/menu/<partner>', handler=MenuHandler, name='menu'),
	('/menu', MenuHandler),
    ('/revieworder', ReviewOrderHandler),
    ('/collection', FormHandler),
    ('/submitted', SubmitHandler),
    
    ('/add', 'admin.InputHandler'),
    ('/upload', 'admin.UploadHandler'),
    ('/delete', 'admin.DeleteHandler'),
    ('/viewpartners', 'admin.ServeHandler'),

    ('/login', CleanerLoginHandler),
    ('/feedback', FeedbackHandler),

    ('/test', TestHandler),

], debug=True)
