# -*- coding: utf-8 -*-

import jinja2
from google.appengine.ext import ndb

import logging
import os.path
import webapp2
 
from webapp2_extras import auth
from webapp2_extras import sessions
from webapp2_extras.auth import InvalidAuthIdError
from webapp2_extras.auth import InvalidPasswordError
from google.appengine.api.urlfetch import DownloadError

from string import split
import csv # for reading the csv

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

import model
import paypal
import logging

from google.appengine.api import mail

try:
  import simplejson as json
except (ImportError,):
  import json

""" UTILITIES """

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

def currencyformat(value):
  if(value % 1 == 0):
    result = "£{:,.0f}".format(value)
  else:
    result = "£{:,.2f}".format(value)
  result = result.decode("utf8")
  return result

def yesnoformat(value):
  if(value == True):
    result = "Yes"
  else:
    result = "No"
  return result

def datetimeformat(value, format='%H:%M %d-%b'):
    return value.strftime(format)

JINJA_ENVIRONMENT.filters['datetimeformat'] = datetimeformat
JINJA_ENVIRONMENT.filters['currencyformat'] = currencyformat
JINJA_ENVIRONMENT.filters['yesnoformat'] = yesnoformat


def user_required(handler):
  """
    Decorator that checks if there's a user associated with the current session.
    Will also fail if there's no session present.
  """
  def check_login(self, *args, **kwargs):
    auth = self.auth
    if not auth.get_user_by_session():
      self.redirect(self.uri_for('partner-login'), abort=True)
    else:
      return handler(self, *args, **kwargs)
 
  return check_login

class BaseHandler(webapp2.RequestHandler):
  @webapp2.cached_property
  def auth(self):
    """Shortcut to access the auth instance as a property."""
    return auth.get_auth()
 
  @webapp2.cached_property
  def user_info(self):
    """Shortcut to access a subset of the user attributes that are stored
    in the session.
 
    The list of attributes to store in the session is specified in
      config['webapp2_extras.auth']['user_attributes'].
    :returns
      A dictionary with most user information
    """
    return self.auth.get_user_by_session()
 
  @webapp2.cached_property
  def user(self):
    """Shortcut to access the current logged in user.
 
    Unlike user_info, it fetches information from the persistence layer and
    returns an instance of the underlying model.
 
    :returns
      The instance of the user model associated to the logged in user.
    """
    u = self.user_info
    return self.user_model.get_by_id(u['user_id']) if u else None
 
  @webapp2.cached_property
  def user_model(self):
    """Returns the implementation of the user model.
 
    It is consistent with config['webapp2_extras.auth']['user_model'], if set.
    """   
    return self.auth.store.user_model
 
  @webapp2.cached_property
  def session(self):
      """Shortcut to access the current session."""
      return self.session_store.get_session(backend="datastore")
 
  def render_template(self, template_filename, params={}):
    user = self.user_info
    params['user'] = user # Params is "template_values"
    template = JINJA_ENVIRONMENT.get_template(os.path.join('templates', 'partner', template_filename))
    self.response.write(template.render(params))

  def display_message(self, message):
    """Utility function to display a template with a simple message."""
    params = {
      'message': message
    }
    self.render_template('message.html', params)
 
  # this is needed for webapp2 sessions to work
  def dispatch(self):
      # Get a session store for this request.
      self.session_store = sessions.get_store(request=self.request)
 
      try:
          # Dispatch the request.
          webapp2.RequestHandler.dispatch(self)
      finally:
          # Save all sessions.
          self.session_store.save_sessions(self.response)

""" User Handlers """

class PartnerHomeHandler(BaseHandler):
  def get(self):
    if self.user != None:
      self.redirect(self.uri_for('partner-dashboard'))

    self.redirect(self.uri_for('partner-login'))

class PartnerSignupHandler(BaseHandler):
  def get(self):
    self.render_template('signup.html')
 
  def post(self):
    user_name = self.request.get('username')
    email = self.request.get('email')
    name = self.request.get('name')
    password = self.request.get('password')
    last_name = self.request.get('lastname')
 
    unique_properties = ['email_address']
    user_data = self.user_model.create_user(user_name,
      unique_properties,
      email_address=email, name=name, password_raw=password,
      last_name=last_name, verified=False)
    if not user_data[0]: #user_data is a tuple
      self.display_message('Unable to create user for email %s because of \
        duplicate keys %s' % (user_name, user_data[1]))
      return
 
    user = user_data[1]
    user_id = user.get_id()
 
    token = self.user_model.create_signup_token(user_id)
 
    verification_url = self.uri_for('partner-verification', type='v', user_id=user_id,
      signup_token=token, _full=True)
 
    # OLD
    msg = 'Send an email to user in order to verify their address. \
          They will be able to do so by visiting  <a href="{url}">{url}</a>'

    # NEW
    # msg = 'We have sent an email to %s with a link that will \
    # enable you to reset your password' % user.email_address

    # partner = get_partner(self.service_partner)

    # from google.appengine.api import mail

    # sender_string = "60 Second Laundry <orders@60secondlaundry.com>"

    # # E.g. New Order: Will Taylor @ 29th May 17:00 - 18:00
    # subject_string = "60 Second Laundry Password Reset"
    
    # to_string = user.email_address
    # body_string = """Hello,

    # Please follow this link to reset your password:

    # <a href="{url}">{url}</a>

    # Any questions about 60 Second Laundry, contact Will on will.taylor@60secondlaundry or call him on 07772622352.

    # The 60 Second Laundry Team
    # We love cleaners!
    # """

    # message = mail.EmailMessage(
    #   sender=sender_string,
    #     subject=subject_string)

    # message.to = to_string
    # message.body = body_string

    # message.send()
 
    self.display_message(msg.format(url=verification_url))

class LogoutHandler(BaseHandler):
  def get(self):
    self.auth.unset_session()
    self.redirect(self.uri_for('partner-home'))

class VerificationHandler(BaseHandler):
  def get(self, *args, **kwargs):
    user = None
    user_id = kwargs['user_id']
    signup_token = kwargs['signup_token']
    verification_type = kwargs['type']
 
    # it should be something more concise like
    # self.auth.get_user_by_token(user_id, signup_token
    # unfortunately the auth interface does not (yet) allow to manipulate
    # signup tokens concisely
    user, ts = self.user_model.get_by_auth_token(int(user_id), signup_token,
      'signup')
 
    if not user:
      logging.info('Could not find any user with id "%s" signup token "%s"',
        user_id, signup_token)
      self.abort(404)
 
    # store user data in the session
    self.auth.set_session(self.auth.store.user_to_dict(user), remember=True)

    if verification_type == 'v':
      # remove signup token, we don't want users to come back with an old link
      self.user_model.delete_signup_token(user.get_id(), signup_token)
 
      if not user.verified:
        user.verified = True
        user.put()
 
      self.display_message('User email address has been verified.')
      return
    elif verification_type == 'p':
      # supply user to the page
      params = {
        'user': user,
        'token': signup_token
      }
      self.render_template('resetpassword.html', params)
    else:
      logging.info('verification type not supported')
      self.abort(404)

class ForgotPasswordHandler(BaseHandler):
  def get(self):
    self._serve_page()

  def post(self):
    username = self.request.get('username')

    user = self.user_model.get_by_auth_id(username)
    if not user:
      logging.info('Could not find any user entry for username %s', username)
      self._serve_page(not_found=True)
      return

    user_id = user.get_id()
    token = self.user_model.create_signup_token(user_id)

    verification_url = self.uri_for('partner-verification', type='p', user_id=user_id,
      signup_token=token, _full=True)

    # msg = 'Send an email to user in order to reset their password. \
    #       They will be able to do so by visiting <a href="{url}">{url}</a>'

    msg = 'We have sent an email to %s with a link that will \
    enable you to reset your password' % user.email_address

    partner = get_partner(self.service_partner)

    from google.appengine.api import mail

    sender_string = "60 Second Laundry <orders@60secondlaundry.com>"
    subject_string = "60 Second Laundry Password Reset"    
    to_string = user.email_address
    body_string = """Hello,

    Please follow this link to reset your password:

    <a href="{url}">{url}</a>

    Any questions about 60 Second Laundry, contact Will on will.taylor@60secondlaundry or call him on 07772622352.

    The 60 Second Laundry Team
    We love cleaners!
    """

    message = mail.EmailMessage(
      sender=sender_string,
        subject=subject_string)

    message.to = to_string
    message.body = body_string

    message.send()

    self.display_message(msg.format(url=verification_url))
  
  def _serve_page(self, not_found=False):
    username = self.request.get('username')
    params = {
      'username': username,
      'not_found': not_found
    }
    self.render_template('forgot.html', params)

class SetPasswordHandler(BaseHandler):

  @user_required
  def post(self):
    password = self.request.get('password')
    old_token = self.request.get('t')

    if not password or password != self.request.get('confirm_password'):
      self.display_message('passwords do not match')
      return

    user = self.user
    user.set_password(password)
    user.put()

    # remove signup token, we don't want users to come back with an old link
    self.user_model.delete_signup_token(user.get_id(), old_token)
    
    self.display_message('Password updated')

""" Profile Handlers """

class DashboardHandler(BaseHandler):
  
  @user_required
  def get(self):
    user = self.user

    partner = model.Partner.get_by_email(user.email_address)
    orders = model.order.get_by_partner_email(user.email_address)

    params = {
      'partner': partner,
      'orders': orders
    }
    self.render_template('dashboard.html', params)

class ViewOrderHandler(BaseHandler):
  
  @user_required
  def get(self, *args, **kwargs):
    
    user = self.user

    partner = model.Partner.get_by_email(user.email_address)
    order_id = kwargs['ordernumber']

    order = model.order.get_by_name_id(partner.name, order_id)

    menuitems = model.menuitem.get_by_partner_name(partner.name)

    message = ''

    template_values ={
      'message': message,
      'order': order,
      'menuitems': menuitems
    }

    template = JINJA_ENVIRONMENT.get_template('templates/partner/order.html')
    self.response.write(template.render(template_values))

class LoginHandler(BaseHandler):
  def get(self):
    self._serve_page()
 
  def post(self):
    username = self.request.get('username')
    password = self.request.get('password')
    try:
      u = self.auth.get_user_by_password(username, password, remember=True)
      self.redirect(self.uri_for('partner-dashboard'))
    except (InvalidAuthIdError, InvalidPasswordError) as e:
      logging.info('Login failed for user %s because of %s', username, type(e))
      self._serve_page(True)
 
  def _serve_page(self, failed=False, message=None):
    username = self.request.get('username')
    print "self.request.get('failed')"
    print self.request.get('failed')
    params = {
      'message': self.request.get('message'),
      'username': username,
      'failed': failed
    }
    self.render_template('login.html', params)

class SubmitOrderHandler(BaseHandler):

  @user_required
  def post(self):

    user = self.user
    username = user.auth_ids[0]
    password = self.request.get('pw')
    ordernumber = self.request.get('ordernumber')
    amount = float(self.request.get('amount'))/100 # receives pence, turns to £

    """ check password """
    try:
      u = self.auth.get_user_by_password(username, password, remember=True)
    except (InvalidAuthIdError, InvalidPasswordError) as e:
      logging.info('Login failed for user %s because of %s', username, type(e))
      params = {
        'password_fail': True,
        'username': username,
      }
      self.render_template('login.html', params)
    """ password accepted """

    """ mis """
    user = self.user
    partner = model.Partner.get_by_email(user.email_address)
    order = model.order.get_by_name_id(partner.name, ordernumber)
    preapproval = model.Preapproval.query(model.Preapproval.order == order.key).get()

    """ charge & receipt customer """
    if order.payment_method == 'cash':
      message = self._charge_cash(order, partner)
    elif order.payment_method == 'paypal':
      message = self._charge_paypal(order, amount, preapproval, partner)

    """ display dashboard again """
    self._display_page(partner, message, user)


  def _charge_cash(self, order, partner):
    if order.charged == False:
      message = "Customer has been sent receipt."
      logging.info( message ) 
      order.charged = True
      order.put()
      self._email_receipt_to_customer(order, partner)
    else:
      message = "Customer been billed previously. This bill was not sent."
      logging.info( message )

  def _charge_paypal(self, order, amount, preapproval, partner):
    if order.charged == False:
      try:
        pay = paypal.PayWithPreapproval( amount=amount, preapproval_key=preapproval.preapproval_key )
        if pay.status() == 'COMPLETED':
          message = "Customer has been billed."
          logging.info( message ) 
          order.charged = True
          order.put()
          self._email_receipt_to_customer(order, partner)
        else:
          print "pay_'ok' response:"
          print pay.response
          message = "ERROR: Customer has not been billed. Please email will.taylor@60secondlaundry.com or call 07772622352"
          logging.info( message )
      except DownloadError:
        message = "ERROR: Unable to connect to internet. Customer has not been billed."
        logging.info( message )
      except:
        print "pay_fail response:"
        print pay.response
        import sys
        print sys.exc_info()[0]
        message = "ERROR: Customer has not been billed. Please email will.taylor@60secondlaundry.com or call 07772622352. Error status:"+ str(sys.exc_info()[0])
        logging.info( message )
    else:
      message = "Customer been billed previously. This bill was not sent."
      logging.info( message )

    return message

  def _email_receipt_to_customer(self, order, partner):

    sender_string = "60 Second Laundry <orders@60secondlaundry.com>"

    subject_string = "Payment Receipt"
    
    order_price = float(order.cost) / 100

    to_string = order.email
    body_string = """
    Hello """ + order.first_name + """,

    Your cleaner has billed you £""" + order_price + """ for your order. """
    
    if order.payment_method == "cash":
      body_string += "You have chosen to pay in cash when your clothes are returned. "
    if order.payment_method == "paypal":
      body_string += "You have chosen to pay by PayPal, so this amount is automatically paid and you do not need to do anything. "

    body_string += """

    Delivery is on """ + self.delivery_time_date + """, unless you have rescheduled with your cleaner.

    If you have any questions or changes with your order, contact your cleaner directly on:
    """ + partner.phonenumber + """


    Order details:
    """ + self.first_name + " " + self.last_name + """
    """ + self.address1

    if self.address2:
      body_string += """
    """ + self.address2

    if self.address3:
      body_string += """
    """ + self.address3

    body_string += """
    """ + self.postcode

    if self.collectioninstructions:
      body_string += """
    """ + self.collectioninstructions

    body_string += """
    Your Phone Number: """ + self.phonenumber + """
    Your Email: """ + self.email + """
    Delivery Time: """ + self.delivery_time_date + """
    Order Reference Number: """ + self.key.id() + """


    If you enjoyed our service, please email Will on will.taylor@60secondlaundry.com


    The 60 Second Laundry Team
    We love cleaners!
    """

    message = mail.EmailMessage(
      sender=sender_string,
        subject=subject_string)

    message.to = to_string
    message.body = body_string

    message.send()

  def _display_page(self, partner, message, user):
    orders = model.order.get_by_partner_email(user.email_address)

    params = {
      'message': message,
      'partner': partner,
      'orders': orders
    }

    template = JINJA_ENVIRONMENT.get_template('templates/partner/dashboard.html')
    self.response.write(template.render(params))



""" BELOW HERE ARE ADMIN TASKS """

def grab(partner_name):
  #This section grabs the data
  fname = "WashingtonDryCleaners.csv"
  

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
    partner_outcodes = partner_outcodes.split()
    partner_address = self.request.get('address')
    partner_minimum_order = self.request.get('minimum_order')
    partner_delivery_cost = self.request.get('delivery_cost')

    partner.phonenumber = self.request.get('phonenumber')
    partner.email = self.request.get('email')

    # Give the new partner our data
    partner.name = partner_name
    partner.address = partner_address
    partner.outcodes = partner_outcodes
    partner.minimum_order = int(partner_minimum_order)
    partner.delivery_cost = partner_delivery_cost

    partner.start_hr = int(self.request.get('start_hr'))
    partner.start_min = int(self.request.get('start_min'))
    partner.end_hr = int(self.request.get('end_hr'))
    partner.end_min = int(self.request.get('end_min'))
    partner.window_size = int(self.request.get('window_size'))


    days = self.request.get('days')
    day_list = days.split()
    day_list = map(int, day_list)
    partner.days = day_list
    
    partner.logo_key = blob_key # n.b. blobstore.BlobReferenceProperty() takes a blob_info
    
    partner.populate_slots()

    # Use to clear all items
    clear_items(partner_name) 

    # Populate if no items exist
    grab(partner_name)

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

