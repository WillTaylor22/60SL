import webapp2
import jinja2
import os

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

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


