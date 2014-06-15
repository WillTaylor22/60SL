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
from datetime import datetime, date, timedelta
import cgi
import logging
from google.appengine.ext.db import Key

from gaesessions import get_current_session

import model
import util
import paypal
import settings

from google.appengine.ext import ndb
from bin import postcode

# Template Settings
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

def nicedates(value):
    today = date.today()
    if value == today:
        return 'Today'
    elif value == (today + timedelta(1)):
        return'Tomorrow'
    elif value.isoweekday() == 1:
        return 'Monday'
    elif value.isoweekday() == 2:
        return 'Tuesday'
    elif value.isoweekday() == 3:
        return 'Wednesday'
    elif value.isoweekday() == 4:
        return 'Thursday'
    elif value.isoweekday() == 5:
        return'Friday'
    elif value.isoweekday() == 6:
        return 'Saturday'
    elif value.isoweekday() == 7:
        return 'Sunday'


JINJA_ENVIRONMENT.filters['datetimeformat'] = datetimeformat
JINJA_ENVIRONMENT.filters['currencyformat'] = currencyformat
JINJA_ENVIRONMENT.filters['nicedates'] = nicedates



# Handlers (Views)
class Main(webapp2.RequestHandler):
    def get(self):
        
        session = get_current_session()
        session['starttime'] = datetime.today()

        template_values = {}

        template = JINJA_ENVIRONMENT.get_template('templates/index.html')
        self.response.write(template.render(template_values))

class Listings(webapp2.RequestHandler):
    def get(self):

        session = get_current_session()

        this_postcode = self.request.get('postcode')

        session['postcode'] = this_postcode

        # analytics
        postcode_attempt = model.postcode_attempt(postcode = this_postcode)
        postcode_attempt.put()

        try:
            outcode = postcode.parse_uk_postcode(this_postcode)[0]

            partners = model.Partner.query(model.Partner.outcodes == outcode).fetch(10)

            if partners[0]:
                template_values = {
                    'postcode' : this_postcode,
                    'partners' : partners
                }
                template = JINJA_ENVIRONMENT.get_template('templates/listings.html')

        except IndexError:
            errormessage = "No supplier at this postcode. We've noted your postcode (" + this_postcode +") and will look for a cleaner near you!"
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


class Menu(webapp2.RequestHandler):
    def get(self):
        
        session = get_current_session()

        partner_name = self.request.get('partner_name')
        
        session['partner'] = partner_name

        if session.has_key('postcode'):
            postcode = session['postcode']

        template_values = {
            'postcode': postcode,
            'partner' : model.get_partner(partner_name),
            'menuitems' : model.menuitem.query(
            ancestor=model.partner_key(partner_name)).order(ndb.GenericProperty("itemid")).fetch(300)
        }

        template = JINJA_ENVIRONMENT.get_template('templates/menu.html')
        self.response.write(template.render(template_values))

class Form(webapp2.RequestHandler):
    def get(self):

        partner_name = self.request.get('partner_name')

        session = get_current_session()

        if session.has_key('postcode'):
            postcode = session['postcode']
        else:
            postcode = ''

        if session.has_key('partner'):
            partner = session['partner']
        else:
            partner = ""

        partner = model.get_partner(partner_name)

        next_three_days = partner.get_next_three_days()

        template_values = {
            "next_three_days": next_three_days,
            "partner_name" : partner_name,
            "postcode": postcode,
            "partner": partner,
        }
        template = JINJA_ENVIRONMENT.get_template('templates/form.html')
        self.response.write(template.render(template_values))

class Review(webapp2.RequestHandler):
    
    # Receives info from Collection(form)
    # then sends user to review the order
    def post(self):

        #creates new order and associates it with the partner
        partner_name = self.request.get('partner_name')

        partner_k = model.partner_key(partner_name)
        myOrder = model.order(parent=partner_k)

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
        myOrder.approx_cost = "Agreed when cleaner sees your clothes"

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


class Buy(webapp2.RequestHandler):
    def get(self):
        template_values = {
            'message': 'You have cancelled your order'
        }
        template = JINJA_ENVIRONMENT.get_template('templates/message.html')
        self.response.write(template.render(template_values))

    # The order has been created and reviewed and submitted
    def post(self):

        ''' start preapproval
        Rather than being associated with a user, each preapproval is associated with an order 

        item        : preapproval_model
        preapproval : preapproval_request

        '''

        session = get_current_session()
        if session.has_key('ordernumber'):
            ordernumber = session['ordernumber']
        if session.has_key('partnername'):
            partnername = session['partnername']

        myOrder_k = ndb.Key('Partner', partnername, 'order', ordernumber)
        myOrder = myOrder_k.get()

        amount = 100 #max payment to take
        item = model.Preapproval( order=myOrder.key, status="NEW", secret=util.random_alnum(16), amount=int(amount*100) )
        item.put()

        # get key
        preapproval = paypal.Preapproval(
          amount=amount,
          return_url="%s/success/%s/%s/" % ( self.request.uri, item.key.id(), item.secret ),
          cancel_url="%s" % self.request.url,
          remote_address=self.request.remote_addr )

        item.debug_request = preapproval.raw_request
        item.debug_response = preapproval.raw_response
        item.put()

        print "item"
        print item

        if preapproval.status() == 'Success':
          item.status = 'CREATED'
          item.preapproval_key = preapproval.key()
          item.put()
          self.redirect( str(preapproval.next_url()) ) # go to paypal
        else:
          item.status = 'ERROR'
          item.status_detail = 'preapproval status was "%s"' % preapproval.status()
          item.put()

        template_values = {
            'message': 'An error occurred connecting to PayPal'
        }
        template = JINJA_ENVIRONMENT.get_template('templates/message.html')
        self.response.write(template.render(template_values))


class Success(webapp2.RequestHandler):
    def get(self, item_id, secret):

        logging.info( "returned from paypal" )

        item = model.Preapproval.get_by_id(int(item_id))

        # validation
        if item == None: # no key
          self.error(404)
          return

        # if item.status != 'CREATED':
        #   item.status_detail = 'Unexpected status %s' % item.status
        #   item.status = 'ERROR'
        #   item.put()
        #   self.error(501)
        #   return
          
        if item.secret != secret:
          item.status_detail = 'Incorrect secret %s' % secret
          item.status = 'ERROR'
          item.put()
          self.error(501)
          return

        item.status = 'COMPLETED'
        item.put()

        timestart = ''
        timetaken = ''
        timeunit = 'seconds'
        session = get_current_session()
        if session.has_key('starttime'):
            timestart = session['starttime']
            timetaken = int((datetime.today() - timestart).total_seconds())
            if timetaken > 60:
                timeunit = "minute"
                if timetaken > 120:
                    timeunit = "minutes"
                timetaken = timetaken/60
        
        if session.has_key('ordernumber'):
            ordernumber = session['ordernumber']
        if session.has_key('partnername'):
            partnername = session['partnername']

        myOrder_k = ndb.Key('Partner', partnername, 'order', ordernumber)
        myOrder = myOrder_k.get()

        query = model.Partner.query(model.Partner.name == myOrder.service_partner)
        partner = query.fetch(1)[0]
        partner_phone_number = partner.phonenumber

        if myOrder:
            myOrder.submitted = True
            myOrder.put()
            if settings.DEBUG == False:
                myOrder.send_txt_to_cleaner()
                myOrder.send_email_to_cleaner()
                myOrder.send_email_to_customer()

        template_values = {
            "partner_phone_number" : partner_phone_number,
            "order" : myOrder,
            "timetaken" : timetaken,
            "timeunit" : timeunit,
        }

        template = JINJA_ENVIRONMENT.get_template('templates/thankyou.html')
        self.response.write(template.render(template_values))

class CleanerLoginHandler(webapp2.RequestHandler):
    def get(self):
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('templates/cleanerlogin.html')
        self.response.write(template.render(template_values))

class FeedbackHandler(webapp2.RequestHandler):
    def post(self):
        myFeedback = model.feedback()
        myFeedback.page = self.request.get('feedback_page')
        myFeedback.feedback = self.request.get('feedback_content')
        myFeedback.put()

class TestHandler(webapp2.RequestHandler):
    def get(self):
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('templates/test.html')
        self.response.write(template.render(template_values))



config = {
  'webapp2_extras.auth': {
    'user_model': 'model.User',
    'user_attributes': ['name']
  },
  'webapp2_extras.sessions': {
    'secret_key': '60SLSECRET'
  }
}

# URL Routing happens here
app = webapp2.WSGIApplication([
    ('/', Main),
    webapp2.Route('/near', handler=Listings, name='near'),
    ('/menu', Menu),
    ('/collection', Form),
    ('/review', Review),
    ('/buy', Buy),
    ('/buy/success/([^/]*)/([^/]*)/.*', Success),
    
    ('/add', 'partner.InputHandler'),
    ('/upload', 'partner.UploadHandler'),
    ('/delete', 'partner.DeleteHandler'),
    ('/viewpartners', 'partner.ServeHandler'),

    webapp2.Route('/partner', 'partner.PartnerHomeHandler', name="partner-home"),
    webapp2.Route('/partner-signup', 'partner.PartnerSignupHandler'),
    webapp2.Route('/partner-verify/<type:v|p>/<user_id:\d+>-<signup_token:.+>',
  handler='partner.VerificationHandler', name='partner-verification'),
    webapp2.Route('/partner-password', 'partner.SetPasswordHandler'),
    webapp2.Route('/partner-login', 'partner.LoginHandler', name='partner-login'),
    webapp2.Route('/partner-logout', 'partner.LogoutHandler', name='partner-logout'),
    webapp2.Route('/partner-forgot', 'partner.ForgotPasswordHandler', name='partner-forgot'),
    webapp2.Route('/partner-dashboard', 'partner.DashboardHandler', name='partner-dashboard'),
    webapp2.Route('/partner/orders/<ordernumber:\d+>', 'partner.ViewOrderHandler', name='partner-view-order'),
    webapp2.Route('/partner/submitorder', 'partner.SubmitOrderHandler', name='partner-submit-order'),


    webapp2.Route('/admin', 'admin.AdminHomeHandler', name="admin-home"),
    webapp2.Route('/admin-signup', 'admin.AdminSignupHandler'),
    webapp2.Route('/admin-verify/<type:v|p>/<user_id:\d+>-<signup_token:.+>',
  handler='admin.VerificationHandler', name='admin-verification'),
    webapp2.Route('/admin-password', 'admin.SetPasswordHandler'),
    webapp2.Route('/admin-login', 'admin.LoginHandler', name='admin-login'),
    webapp2.Route('/admin-logout', 'admin.LogoutHandler', name='admin-logout'),
    webapp2.Route('/admin-forgot', 'admin.ForgotPasswordHandler', name='admin-forgot'),
    webapp2.Route('/admin-dashboard', 'admin.AuthenticatedHandler', name='admin-authenticated'),

    ('/feedback', FeedbackHandler),

    ('/test', TestHandler),

], debug=True, config=config)
