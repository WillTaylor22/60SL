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
import math
from operator import attrgetter
from datetime import datetime, date, timedelta
import cgi
import logging
from google.appengine.ext.db import Key

from gaesessions import get_current_session

import model
import util
import paypal
import settings
from google.appengine.api import mail

from google.appengine.ext import ndb
from bin import postcode

# import webapp2_extras
from webapp2_extras.routes import PathPrefixRoute

# Template Settings
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape', "jinja2.ext.do"],
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

def distanceformat(value):
    if value >= 1000:
        result = str(int(round(float(value)/1000))) + "km away"
    else:
        result = str(value) + "m away"
    return result

e = jinja2.Environment()
JINJA_ENVIRONMENT.filters['datetimeformat'] = datetimeformat
JINJA_ENVIRONMENT.filters['currencyformat'] = currencyformat
JINJA_ENVIRONMENT.filters['nicedates'] = nicedates
JINJA_ENVIRONMENT.filters['distanceformat'] = distanceformat


# Handlers (Views)
class Main(webapp2.RequestHandler):
    def get(self):
        
        session = get_current_session()
        session['starttime'] = datetime.today()

        template_values = {}

        template = JINJA_ENVIRONMENT.get_template('templates/index.html')
        self.response.write(template.render(template_values))

class MobileHome(webapp2.RequestHandler):
    def get(self):
        
        session = get_current_session()
        session['starttime'] = datetime.today()

        template_values = {}

        template = JINJA_ENVIRONMENT.get_template('templates/index-mobile.html')
        self.response.write(template.render(template_values))


class Listings(webapp2.RequestHandler):
    def get(self):
        print "here"
        session = get_current_session()

        # Load from session if using breadcrumb
        this_postcode = self.request.get('postcode')
        if this_postcode == '':
            if session.has_key('postcode'):
                this_postcode = session['postcode']

        session['postcode'] = this_postcode

        # Load from session if using breadcrumb
        lat = self.request.get('lat')
        if lat == '':
            if session.has_key('latitude'):
                lat = session['latitude']

        session['latitude'] = lat

        lon = self.request.get('long')
        if lon == '':
            if session.has_key('longitude'):
                lon = session['longitude']

        session['longitude'] = lon

        latitude = float(lat)
        longitude = float(lon)

        # this tells you a distance has been found.
        # if not found, skip distance calculations
        distanceflag = 0
        if latitude:
            if longitude:
                distanceflag = 1

        # analytics
        _postcode_attempt = model.postcode_attempt(postcode = this_postcode)
        _postcode_attempt.put()

        try:
            outcode = postcode.parse_uk_postcode(this_postcode, strict=True, incode_mandatory=False)[0]

            partners = model.Partner.query(model.Partner.outcodes == outcode).fetch(10)
            sortflag = 1  # for skipping sort if not all distances found
            if partners[0]:
                if distanceflag == 1: # for skipping if customer location not found
                    for partner in partners:
                        if partner.latitude:
                            if partner.longitude:
                                lat1 = partner.latitude
                                lat2 = latitude
                                lon1 = partner.longitude
                                lon2 = longitude
                                distance = get_distance(lat1, lat2, lon1, lon2)
                                partner.distance = round_to_1(distance)  
                            else:
                                sortflag = 0
                        else:
                            sortflag = 0
                if sortflag == 1: # all distances found, sort allowed...
                    partners.sort(key=attrgetter('distance'))


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

def round_to_1(x):
    if x == 0:
        return 0
    else:
        return int(round(x, -int(math.floor(math.log10(x)))))

def get_distance(lat1, lat2, lon1, lon2):
    R = 6371000 # m
    theta_1 = math.radians(lat1)
    theta_2 = math.radians(lat2)
    delta_theta = math.radians(lat2-lat1)
    delta_lamda = math.radians(lon2-lon1)

    a = math.sin(delta_theta/2) * math.sin(delta_theta/2) + \
        math.cos(theta_1) * math.cos(theta_2) * math.sin(delta_lamda/2) * \
        math.sin(delta_lamda/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c;


class Menu(webapp2.RequestHandler):
    def get(self):
        
        session = get_current_session()

        partner_name = self.request.get('partner_name')

        # Load from session if using breadcrumb
        if partner_name == '':
            if session.has_key('partner'):
                partner_name = session['partner']
        
        session['partner'] = partner_name


        if session.has_key('postcode'):
            postcode = session['postcode']

        partner = model.get_partner(partner_name)
        menuitems = model.menuitem.query(
            ancestor=model.partner_key(partner.name)).order(ndb.GenericProperty("itemid")).fetch(300)

        print partner.name
        print partner.key
        print menuitems

        template_values = {
            'postcode': postcode,
            'partner' : partner,
            'menuitems' : menuitems
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

        print "IN REVIEW"
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
        myOrder.payment_method = self.request.get('payment_method')

        myOrder.put()

        session = get_current_session()
        session['ordernumber'] = myOrder.key.id()
        session['partnername'] = partner_name

        continue_message = ''
        if myOrder.payment_method == 'cash':
            continue_message = 'You are paying in cash when your cleaned clothes are delivered.'
        elif myOrder.payment_method == 'paypal':
            continue_message = 'You are billed automatically when your cleaner confirms the price. Continue to PayPal to complete your order. '

        template_values = {
            "continue_message": continue_message,
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

        session = get_current_session()
        if session.has_key('ordernumber'):
            ordernumber = session['ordernumber']
        if session.has_key('partnername'):
            partnername = session['partnername']

        myOrder_k = ndb.Key('Partner', partnername, 'order', ordernumber)
        myOrder = myOrder_k.get()

        if myOrder.payment_method == 'paypal':
            self._start_preapproval(ordernumber, partnername, myOrder)
        if myOrder.payment_method == 'cash':
            self.redirect(self.uri_for('success-cash'))

    def _start_preapproval(self, ordernumber, partnername, myOrder):
        ''' start preapproval
        Rather than being associated with a user, each preapproval is associated with an order 

        item        : preapproval_model
        preapproval : preapproval_request

        '''

        amount = 200 # max payment to take, £
        item = model.Preapproval( order=myOrder.key, status="NEW", secret=util.random_alnum(16), amount=amount )
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

class SuccessCash(webapp2.RequestHandler):
    def get(self):
        _display_success_page(self)

class SuccessPayPal(webapp2.RequestHandler):
    def get(self, item_id, secret):

        logging.info( "returned from paypal" )

        item = model.Preapproval.get_by_id(int(item_id))

        # validation
        if item == None: # no key
          self.error(404)
          return

        if item.status != 'CREATED':
          item.status_detail = 'Unexpected status %s' % item.status
          item.status = 'ERROR'
          item.put()
          logging.info( item.status )
          logging.info( item.status_detail )
          self.error(501)
          return
          
        if item.secret != secret:
          item.status_detail = 'Incorrect secret %s' % secret
          item.status = 'ERROR'
          item.put()
          logging.info( item.status )
          logging.info( item.status_detail )
          self.error(501)
          return

        item.status = 'COMPLETED'
        item.put()

        _display_success_page(self)
    
def _display_success_page(rq):
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
            myOrder.send_email_to_will()

    template_values = {
        "partner_phone_number" : partner_phone_number,
        "order" : myOrder,
        "timetaken" : timetaken,
        "timeunit" : timeunit,
    }

    template = JINJA_ENVIRONMENT.get_template('templates/thankyou.html')
    rq.response.write(template.render(template_values))

class PrivacyHandler(webapp2.RequestHandler):
    def get(self):
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('templates/privacy.html')
        self.response.write(template.render(template_values))

class TermsHandler(webapp2.RequestHandler):
    def get(self):
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('templates/terms.html')
        self.response.write(template.render(template_values))

class ContactHandler(webapp2.RequestHandler):
    def get(self):
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('templates/contact.html')
        self.response.write(template.render(template_values))

    def post(self):
        name = self.request.get('InputName')
        email = self.request.get('InputEmail')
        message = self.request.get('InputMessage')

        print name
        print email
        print message

        sender_string = "60 Second Laundry <orders@60secondlaundry.com>"

        subject_string = "New Message from " + name


        message = mail.EmailMessage(
            sender=sender_string,
            subject=subject_string)

        message.to = 'will.taylor@60secondlaundry.com'
        message.body = message

        message.send()


        success = True
        template_values = {
            'success': True,
        }
        template = JINJA_ENVIRONMENT.get_template('templates/contact.html')
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
    ('/m', MobileHome),
    webapp2.Route('/near', handler=Listings, name='near'),
    ('/menu', Menu),
    ('/collection', Form),
    ('/review', Review),
    ('/buy', Buy),
    webapp2.Route('/buy/success', handler=SuccessCash, name="success-cash"),
    ('/buy/success/([^/]*)/([^/]*)/.*', SuccessPayPal),

    ('/add', 'admin.InputHandler'),
    ('/upload', 'admin.UploadHandler'),
    ('/delete', 'admin.DeleteHandler'),
    ('/viewpartners', 'admin.ServeHandler'),
    ('/addmenu', 'admin.AddMenuHandler'),
    ('/addshirts', 'admin.AddShirtsHandler'),
    ('/addgeocode', 'admin.AddGeocodeHandler'),


    PathPrefixRoute('/partner', [
        webapp2.Route('/signup', 'partner.PartnerSignupHandler'),
        webapp2.Route('/verify/<type:v|p>/<user_id:\d+>-<signup_token:.+>',
        handler='partner.VerificationHandler', name='partner-verification'),
        webapp2.Route('/password', 'partner.SetPasswordHandler'),
        webapp2.Route('/login', 'partner.LoginHandler', name='partner-login'),
        webapp2.Route('/logout', 'partner.LogoutHandler', name='partner-logout'),
        webapp2.Route('/forgot', 'partner.ForgotPasswordHandler', name='partner-forgot'),
        webapp2.Route('/', 'partner.DashboardHandler', name='partner'),
        webapp2.Route('/orders/<ordernumber:\d+>', 'partner.ViewOrderHandler', name='partner-view-order'),
        webapp2.Route('/submitorder', 'partner.SubmitOrderHandler', name='partner-submit-order'),
        webapp2.Route('/reviews', 'partner.ReviewsHandler', name='partner-reviews'),
        webapp2.Route('/menu', 'partner.MenuHandler', name='partner-menu'),
        webapp2.Route('/menu/<itemnumber:\d+>', 'partner.ViewMenuItemHandler', name='partner-view-item'),
        webapp2.Route('/info', 'partner.InfoHandler', name='partner-info'),
        webapp2.Route('/settings', 'partner.SettingsHandler', name='partner-settings'),
        webapp2.Route('/password-dashboard', 'partner.SetPasswordDashboardHandler'),
    ]),

    ('/privacy', PrivacyHandler),
    ('/terms', TermsHandler),
    ('/feedback', FeedbackHandler),
    ('/contact', ContactHandler),

    ('/test', TestHandler),

], debug=True, config=config)