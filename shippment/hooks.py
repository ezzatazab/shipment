app_name = "shippment"
app_title = "shippment"
app_publisher = "NSFSS"
app_description = "service shippment"
app_email = "Ezzat.orc@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "shippment",
# 		"logo": "/assets/shippment/logo.png",
# 		"title": "shippment",
# 		"route": "/shippment",
# 		"has_permission": "shippment.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/shippment/css/shippment.css"
# app_include_js = "/assets/shippment/js/shippment.js"

# include js, css files in header of web template
# web_include_css = "/assets/shippment/css/shippment.css"
# web_include_js = "/assets/shippment/js/shippment.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "shippment/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Sales Invoice" : "public/js/sales_invoice.js",
    "Purchase Invoice" : "public/js/purchase_invoice.js",
    "Shipment" : "public/js/shipment.js",
    "User" : "public/js/user.js",
    "Journal Entry" : "public/js/journal_entry.js"
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "shippment/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "shippment.utils.jinja_methods",
# 	"filters": "shippment.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "shippment.install.before_install"
# after_install = "shippment.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "shippment.uninstall.before_uninstall"
# after_uninstall = "shippment.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "shippment.utils.before_app_install"
# after_app_install = "shippment.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "shippment.utils.before_app_uninstall"
# after_app_uninstall = "shippment.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "shippment.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Payment Request": "shippment.overrides.payment_request.CustomPaymentRequest"
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Shipment": {
		# "validate": "shippment.overrides.shipment.set_shipment_service",
        "on_update": "shippment.overrides.shipment.update_vessel_detail",
	},
    "Purchase Invoice": {
        "after_insert": "shippment.overrides.purchase_invoice.link_customs_shipment"
    },
    "Journal Entry": {
        "validate": "shippment.overrides.journal_entry.set_party_name"
    }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"shippment.tasks.all"
# 	],
# 	"daily": [
# 		"shippment.tasks.daily"
# 	],
# 	"hourly": [
# 		"shippment.tasks.hourly"
# 	],
# 	"weekly": [
# 		"shippment.tasks.weekly"
# 	],
# 	"monthly": [
# 		"shippment.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "shippment.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "shippment.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "shippment.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["shippment.utils.before_request"]
# after_request = ["shippment.utils.after_request"]

# Job Events
# ----------
# before_job = ["shippment.utils.before_job"]
# after_job = ["shippment.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"shippment.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }



fixtures = [
    "Ports",
    "Shipment Status",
    "Type of Shipping"
]