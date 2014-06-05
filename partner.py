import jinja2
from google.appengine.ext import ndb

import logging
import os.path
import webapp2
 
from webapp2_extras import auth
from webapp2_extras import sessions

from webapp2_extras.auth import InvalidAuthIdError
from webapp2_extras.auth import InvalidPasswordError


from string import split

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


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

class PartnerHomeHandler(BaseHandler):
  def get(self):
    self.render_template('home.html')

class PartnerSignupHandler(BaseHandler):

  @user_required
  def get(self):

    upload_url = blobstore.create_upload_url('/partner-signup')   # create upload_url for uploading picture

    params ={
      'upload_url': upload_url
    }

    self.render_template('signup.html', params)
 
  def post(self):
    if self.request.get('adminpassword') != "SuperSecretPassword":
      self.redirect(self.uri_for('partner-home'))

    # collect info
    email = self.request.get('email')
    phonenumber = self.request.get('phonenumber')
    name = self.request.get('name')
    password = self.request.get('password')
    last_name = self.request.get('lastname')

    outcodes = self.request.get('outcodes').split()
    address = self.request.get('address')
    minimum_order = int(self.request.get('minimum_order'))
    delivery_cost = self.request.get('delivery_cost')

    start_hr = int(self.request.get('start_hr'))
    start_min = int(self.request.get('start_min'))
    end_hr = int(self.request.get('end_hr'))
    end_min = int(self.request.get('end_min'))
    window_size = int(self.request.get('window_size'))
    days = map(int, self.request.get('days').split())

    upload_files = self.get_uploads('logo')  # Blob data: ('logo' is file upload field in the form)
    blob_info = upload_files[0]
    logo_key = blob_info.key()

    unique_properties = ['email_address']
    user_data = self.user_model.create_user(unique_properties,
      email_address=email, name=name, password_raw=password,
      last_name=last_name, outcodes=outcodes, address=address,
      minimum_order = minimum_order, delivery_cost = delivery_cost,
      start_hr = start_hr, start_min = start_min, end_hr = end_hr,
      end_min = end_min, window_size = window_size, days = days,
      logo_key = logo_key,
      verified=True)
    if not user_data[0]: #user_data is a tuple
      self.display_message('Unable to create user for email %s because of \
        duplicate keys %s' % (email, user_data[1]))
      return

    # model stuff:
    # partner.populate_slots()
    # clear_items(partner_name)     # Use to clear all items TODO: partner.clear_items() 
    # grab(partner_name)      # Populate if no items exist TODO: partner.grab()

    self.display_message("Partner Created")



class LoginHandler(BaseHandler):
  def get(self):
    self._serve_page()
 
  def post(self):
    username = self.request.get('username')
    password = self.request.get('password')
    try:
      u = self.auth.get_user_by_password(username, password, remember=True)
      self.redirect(self.uri_for('partner-home'))
    except (InvalidAuthIdError, InvalidPasswordError) as e:
      logging.info('Login failed for user %s because of %s', username, type(e))
      self._serve_page(True)
 
  def _serve_page(self, failed=False):
    username = self.request.get('username')
    params = {
      'username': username,
      'failed': failed
    }
    self.render_template('login.html', params)

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

    msg = 'Send an email to user in order to reset their password. \
          They will be able to do so by visiting <a href="{url}">{url}</a>'

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

class AuthenticatedHandler(BaseHandler):
  @user_required
  def get(self):
    user = self.user

    partner = mymodels.get_partner(partner_name)
    orders = mymodels.get_orders(partner_name)

    params = {
      'partner': user,
      'orders': orders
    }
    self.render_template('dashboard.html', params)

class PartnerLoginHandler(webapp2.RequestHandler):
  def get(self):
    template_values ={}

    template = JINJA_ENVIRONMENT.get_template('templates/partner/login.html')
    self.response.write(template.render(template_values))

class PartnerDashboardHandler(webapp2.RequestHandler):
  def get(self):
    query = mymodels.Partner.query(mymodels.Partner.name == partner_name)
    partner = query.fetch(1)[0]


    template_values ={
      'partner': partner,
    }

    template = JINJA_ENVIRONMENT.get_template('templates/partner/dashboard.html')
    self.response.write(template.render(template_values))

class PartnerNewOrderHandler(webapp2.RequestHandler):
  def get(self):
    template_values ={
    }

    template = JINJA_ENVIRONMENT.get_template('templates/partner/new_order.html')
    self.response.write(template.render(template_values))

class PartnerInfoHandler(webapp2.RequestHandler):
  def get(self):
    template_values ={
    }

    template = JINJA_ENVIRONMENT.get_template('templates/partner/info.html')
    self.response.write(template.render(template_values))

class PartnerMenuHandler(webapp2.RequestHandler):
  def get(self):
    
    template_values ={
    }

    template = JINJA_ENVIRONMENT.get_template('templates/partner/menu.html')
    self.response.write(template.render(template_values))


class InputHandler(webapp2.RequestHandler):
  def get(self): # this page is ONLY for input of partners
    

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
    partner = mymodels.Partner(parent=mymodels.partner_key(partner_name))

    
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
    partner_query = mymodels.Partner.query()
    partners = partner_query.fetch(50)

    template_values ={
      'partners': partners,
    }

    template = JINJA_ENVIRONMENT.get_template('templates/admin/viewpartners.html')
    self.response.write(template.render(template_values))

class DeleteHandler(webapp2.RequestHandler):
  def post(self): # this page is ONLY for input of partners
    partner_name = self.request.get('partner_name')

    q = mymodels.Partner.query(mymodels.Partner.name == partner_name)
    results = q.fetch(10)
    
    for result in results:
      result.key.delete()

    self.redirect('/viewpartners')        


