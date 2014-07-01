# -*- coding: utf-8 -*-

import jinja2
from google.appengine.ext import ndb

import logging
import os.path
import webapp2
 
from webapp2_extras import auth, sessions, security
from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError
from google.appengine.api.urlfetch import DownloadError

from string import split
import csv # for reading the csv

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

import model
from model import Partner, order, menuitem, Preapproval
import paypal
import logging

from django.utils import simplejson as json

from google.appengine.api import mail
import quopri # for "= every 75 char" bug


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

def badgecollapseformat(value):
  if(value == 0):
    result = ""
  else:
    result = value
  return result

def datetimeformat(value, format='%H:%M %d-%b'):
    return value.strftime(format)

JINJA_ENVIRONMENT.filters['datetimeformat'] = datetimeformat
JINJA_ENVIRONMENT.filters['currencyformat'] = currencyformat
JINJA_ENVIRONMENT.filters['yesnoformat'] = yesnoformat
JINJA_ENVIRONMENT.filters['badgecollapseformat'] = badgecollapseformat

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
    params['user_info'] = user # Params is "template_values"
    template = JINJA_ENVIRONMENT.get_template(os.path.join('templates', 'partner', template_filename))
    self.response.write(template.render(params))

  def render_template_dashboard(self, template_filename, user, partner, params={}):
    params['user'] = user
    params['partner'] = partner
    num_orders = order.get_outstanding_by_partner_email(partner.email)
    params['num_orders'] = num_orders
    params['num_reviews'] = 0
    self.render_template(template_filename, params)


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


class LoginHandler(BaseHandler):
  def get(self):
    self._serve_page()
 
  def post(self):
    username = self.request.get('username')
    password = self.request.get('password')
    try:
      u = self.auth.get_user_by_password(username, password, remember=True)
      self.redirect(self.uri_for('partner'))
    except (InvalidAuthIdError, InvalidPasswordError) as e:
      logging.info('Login failed for user %s because of %s', username, type(e))
      self._serve_page(True)
 
  def _serve_page(self, failed=False, message=None):
    username = self.request.get('username')
    params = {
      'message': self.request.get('message'),
      'username': username,
      'failed': failed
    }
    self.render_template('login.html', params)


class LogoutHandler(BaseHandler):
  def get(self):
    self.auth.unset_session()
    self.redirect(self.uri_for('partner-login'))

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

    partner = Partner_key_by_email(user.email_address).get()

    from google.appengine.api import mail

    sender_string = "60 Second Laundry <orders@60secondlaundry.com>"
    subject_string = "60 Second Laundry Password Reset"    
    to_string = user.email_address
    body_string = """Hello,

Please follow this link to reset your password:

""" + verification_url + """"

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

class SetPasswordDashboardHandler(BaseHandler):

  @user_required
  def post(self):

    user = self.user
    username = user.auth_ids[0]

    current_password = self.request.get('current_password')

    """ check password """
    if not security.check_password_hash(current_password, user.password):

      logging.info('Change password in dashboard failed for user %s', username)
      params = {
        'message': '"Current password" was not correct'
      }
      partner = Partner.get_by_email(user.email_address)
      self.render_template_dashboard('settings.html', user, partner, params)
    """ password accepted """

    password = self.request.get('password')
    partner = Partner.get_by_email(user.email_address)

    if not password or password != self.request.get('confirm_password'):
      params = {
        message: 'passwords do not match'
      }
      self.render_template_dashboard('settings.html', user, partner, params)
      return

    user.set_password(password)
    user.put()
    
    params = {
      'message': 'Password changed!'
    }
    self.render_template_dashboard('settings.html', user, partner, params)



""" Profile Handlers """

class DashboardHandler(BaseHandler):
  
  @user_required
  def get(self):
    user = self.user
    partner = Partner.get_by_email(user.email_address)
    
    orders = order.get_by_partner_email(user.email_address)

    params = {
      'orders': orders
    }

    self.render_template_dashboard('orders.html', user, partner, params)

class ViewOrderHandler(BaseHandler):
  
  @user_required
  def get(self, *args, **kwargs):
    
    user = self.user

    partner = Partner.get_by_email(user.email_address)
    order_id = kwargs['ordernumber']

    _order = order.get_by_name_id(partner.name, order_id)

    menuitems = menuitem.get_by_partner_name(partner.name)

    message = ''

    params = {
      'message': message,
      'order': _order,
      'menuitems': menuitems
    }

    self.render_template_dashboard('order.html', user, partner, params)


class SubmitOrderHandler(BaseHandler):

  @user_required
  def post(self):

    user = self.user
    password = self.request.get('pw')
    ordernumber = self.request.get('ordernumber')
    amount = float(self.request.get('amount'))/100 # receives pence, turns to £
    partner = Partner.get_by_email(user.email_address)


    """ check password """
    if not security.check_password_hash(current_password, user.password):
      logging.info('Login failed for user %s because of %s', username, type(e))

      orders = order.get_by_partner_email(user.email_address)

      params = {
        'orders': orders
      }

      self.render_template_dashboard('orders.html', user, partner, params)
    """ password accepted """


   

    """ mis """
    order = order.get_by_name_id(partner.name, ordernumber)
    preapproval = Preapproval.query(Preapproval.order == order.key).get()
    message = ''

    """ charge & receipt customer """
    if order.payment_method == 'cash':
      message = self._charge_cash(order, partner, amount)
    elif order.payment_method == 'paypal':
      message = self._charge_paypal(order, amount, preapproval, partner)

    self._send_me_email(order, partner)

    """ display dashboard again """
    self._display_page(partner, message, user)


  def _charge_cash(self, order, partner, amount):
    if order.charged == False:
      message = "Customer has been sent receipt."
      logging.info( message ) 
      order.charged = True
      order.cost = amount
      order.put()
      self._email_receipt_to_customer(order, partner)
    else:
      message = "Customer been billed previously. This bill was not sent."
      logging.info( message )

    return message

  def _charge_paypal(self, order, amount, preapproval, partner):
    if order.charged == False:
      try:
        pay = paypal.PayWithPreapproval( amount=amount, preapproval_key=preapproval.preapproval_key )
        if pay.status() == 'COMPLETED':
          message = "Customer has been billed."
          logging.info( message ) 
          order.charged = True
          order.cost = amount
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
      # except:
      #   import sys
      #   print sys.exc_info()[0]
      #   message = "ERROR: Customer has not been billed. Please email will.taylor@60secondlaundry.com or call 07772622352. Error status:"+ str(sys.exc_info()[0])
      #   logging.info( message )
    else:
      message = "Customer been billed previously. This bill was not sent."
      logging.info( message )

    return message


  def _send_me_email(self, order, partner):

    sender_string = "60 Second Laundry <orders@60secondlaundry.com>"

    subject_string = "Order Submit By Cleaner"

    order_cost = str(order.cost)
    print "type(order_cost)"
    print type(order_cost)

    to_string = 'wrftaylor@gmail.com'
    body_string = """
    Hello """ 
    body_string += order.first_name
    body_string += """,

    Your cleaner has billed you """

    body_string += "&#xA3"
    body_string += order_cost
    body_string += " for your order. "
    
    if order.payment_method == "cash":
      body_string += "You have chosen to pay in cash when your clothes are returned. "
    if order.payment_method == "paypal":
      body_string += "You have chosen to pay by PayPal, so this amount is automatically paid and you do not need to do anything. "

    body_string += """

    Delivery is on """ + order.delivery_time_date + """, unless you have rescheduled with your cleaner.

    If you have any questions or changes with your order, contact your cleaner directly on:
    """ + partner.phonenumber + """


    Order details:
    """ + order.first_name + " " + order.last_name + """
    """ + order.address1

    if order.address2:
      body_string += """
    """ + order.address2

    if order.address3:
      body_string += """
    """ + order.address3

    body_string += """
    """ + order.postcode

    if order.collectioninstructions:
      body_string += """
    """ + order.collectioninstructions

    body_string += """
    Your Phone Number: """ + order.phonenumber + """
    Your Email: """ + order.email + """
    Delivery Time: """ + order.delivery_time_date + """
    Order Reference Number: """ + str(order.key.id()) + """


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

  def _email_receipt_to_customer(self, order, partner):

    sender_string = "60 Second Laundry <orders@60secondlaundry.com>"

    subject_string = "Payment Receipt"

    order_cost = str(order.cost)
    print "type(order_cost)"
    print type(order_cost)

    to_string = order.email
    body_string = """
    Hello """ 
    body_string += order.first_name
    body_string += """,

    Your cleaner has billed you """

    body_string += "&#xA3"
    body_string += order_cost
    body_string += " for your order. "
    
    if order.payment_method == "cash":
      body_string += "You have chosen to pay in cash when your clothes are returned. "
    if order.payment_method == "paypal":
      body_string += "You have chosen to pay by PayPal, so this amount is automatically paid and you do not need to do anything. "

    body_string += """

    Delivery is on """ + order.delivery_time_date + """, unless you have rescheduled with your cleaner.

    If you have any questions or changes with your order, contact your cleaner directly on:
    """ + partner.phonenumber + """


    Order details:
    """ + order.first_name + " " + order.last_name + """
    """ + order.address1

    if order.address2:
      body_string += """
    """ + order.address2

    if order.address3:
      body_string += """
    """ + order.address3

    body_string += """
    """ + order.postcode

    if order.collectioninstructions:
      body_string += """
    """ + order.collectioninstructions

    body_string += """
    Your Phone Number: """ + order.phonenumber + """
    Your Email: """ + order.email + """
    Delivery Time: """ + order.delivery_time_date + """
    Order Reference Number: """ + str(order.key.id()) + """


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
    orders = order.get_by_partner_email(user.email_address)

    params = {
      'message': message,
      'partner': partner,
      'orders': orders
    }

    template = JINJA_ENVIRONMENT.get_template('templates/partner/dashboard.html')
    self.response.write(template.render(params))


class ReviewsHandler(BaseHandler):
  
  @user_required
  def get(self, *args, **kwargs):
    
    user = self.user
    partner = Partner.get_by_email(user.email_address)

    message = ''

    params = {
      'message': message,
    }

    self.render_template_dashboard('reviews.html', user, partner, params)


class MenuHandler(BaseHandler):
  
  @user_required
  def get(self, *args, **kwargs):
    
    user = self.user
    partner = Partner.get_by_email(user.email_address)

    menuitems = menuitem.get_by_partner_name(partner.name)

    message = ''

    params = {
      'user': user,
      'message': message,
      'menuitems': menuitems
    }

    self.render_template_dashboard('menu.html', user, partner, params)
    

class ViewMenuItemHandler(BaseHandler):
  
  @user_required
  def get(self, *args, **kwargs):
    
    user = self.user

    partner = Partner.get_by_email(user.email_address)
    item_id = kwargs['itemnumber']

    # menuitems = menuitem.get_by_partner_name(partner.name)
    # print menuitems

    _menuitem = menuitem.get_by_partner_name_id(partner.name, item_id)

    message = ''

    params = {
      'message': message,
      'item': _menuitem
    }

    self.render_template_dashboard('menuitem.html', user, partner, params)




class InfoHandler(BaseHandler):
  
  @user_required
  def get(self, *args, **kwargs):
    
    user = self.user
    partner = Partner.get_by_email(user.email_address)

    upload_url = blobstore.create_upload_url('/partner/profile-photo')

    message = ''

    params = {
      'upload_url': upload_url,
      'user': user,
      'message': message,
    }

    self.render_template_dashboard('info.html', user, partner, params)

  @user_required
  def post(self):
    user = self.user
    partner = Partner.get_by_email(user.email_address)

    upload_url = blobstore.create_upload_url('/partner/profile-photo')

    # Basic Information
    partner.info_enable = self.request.get('info_enable') != ''
    partner.manager_name = self.request.get('manager_name')
    partner.manager_introduction = self.request.get('manager_introduction')
    partner.about_us = self.request.get('about_us')
    partner.terms = self.request.get('terms')
    partner.put()

    message = 'Saved.'

    params = {
      'upload_url': upload_url,
      'user': user,
      'message': message,
    }

    self.render_template_dashboard('info.html', user, partner, params)


class ProfilePhotoHandler(blobstore_handlers.BlobstoreUploadHandler, BaseHandler):
  
  @user_required
  def post(self):
    user = self.user
    partner = Partner.get_by_email(user.email_address)

    upload_url = blobstore.create_upload_url('/partner/profile-photo')

    upload_files = self.get_uploads('profile_photo')


    blob_info = upload_files[0]
    blob_key = blob_info.key()
    partner.profile_key = blob_key
    partner.put()

    message = 'Photo Saved.'

    params = {
      'upload_url': upload_url,
      'user': user,
      'message': message,
    }

    self.render_template_dashboard('info.html', user, partner, params)


class SettingsHandler(BaseHandler):

  @user_required
  def get(self, *args, **kwargs):
    
    user = self.user
    partner = Partner.get_by_email(user.email_address)

    message = ''

    params = {
      'user': user,
      'message': message,
    }

    self.render_template_dashboard('settings.html', user, partner, params)

  @user_required
  def post(self):

    user = self.user
    partner = Partner.get_by_email(user.email_address)

    # Basic Information
    partner.name = self.request.get('name')
    partner.address = self.request.get('address')

    
    # Contacting you
    partner.phonenumber = self.request.get('phonenumber')
    partner.phonenumber_2 = self.request.get('phonenumber_2')
    partner.email_2 = self.request.get('email_2')
    partner.email_3 = self.request.get('email_3')


    # Delivery Locations
    # - Outcodes
    partner_outcodes = self.request.get('outcodes')
    partner_outcodes = quopri.decodestring(partner_outcodes)
    partner.outcodes = partner_outcodes.split()
    # - Free Delivery
    partner.minimum_order = int(self.request.get('minimum_order'))
    # - Paid Delivery
    partner.minimum_order_paid_accept = self.request.get('minimum_order_paid_accept') != ''
    partner.minimum_order_paid = int(self.request.get('minimum_order_paid'))
    print "partner.minimum_order_paid_accept"
    print partner.minimum_order_paid_accept
    
    # Delivery Times
    # - Start
    partner.start_hr = int(self.request.get('start_hr'))
    partner.start_min = int(self.request.get('start_min'))
    # - End
    partner.end_hr = int(self.request.get('end_hr'))
    partner.end_min = int(self.request.get('end_min'))
    # - Window
    partner.window_size = int(self.request.get('window_size'))
    # - Days
    days = self.request.get('days')
    day_list = days.split()
    day_list = map(int, day_list)
    partner.days = day_list


    # Optional Delivery Settings
    # - Last orders same evening
    partner.last_orders_same_day_enable = self.request.get('last_orders_same_day_enable') != ''
    partner.last_orders_same_day_hr = int(self.request.get('last_orders_same_day_hr'))
    partner.last_orders_same_day_min = int(self.request.get('last_orders_same_day_min'))
    # - Last orders next morning
    partner.last_orders_enable = self.request.get('last_orders_enable') != ''
    partner.last_orders_hr = int(self.request.get('last_orders_hr'))
    partner.last_orders_min = int(self.request.get('last_orders_min'))
    partner.end_of_morning_hr = int(self.request.get('end_of_morning_hr'))
    partner.end_of_morning_min = int(self.request.get('end_of_morning_min'))

    partner.put()

    # redirect
    message = 'Changes saved.'

    params = {
      'user': user,
      'message': message,
    }

    self.render_template_dashboard('settings.html', user, partner, params)