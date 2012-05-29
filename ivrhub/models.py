''' mongoengine models
'''
from mongoengine import *


class User(Document):
    ''' some are admins some are not
    '''
    admin_rights = BooleanField(required=True)
    api_id = StringField()
    api_key = StringField()
    email = EmailField(required=True, unique=True, max_length=254)
    email_confirmation_code = StringField(required=True)
    email_confirmed = BooleanField(required=True)
    forgot_password_code = StringField()
    last_login_time = DateTimeField(required=True)
    name = StringField()
    organizations = ListField(ReferenceField('Organization'))
    password_hash = StringField(required=True)
    registration_time = DateTimeField(required=True)
    verified = BooleanField(required=True)


class Organization(Document):
    ''' people join orgs
    '''
    description = StringField(default='')
    location = StringField()
    # url-safe version of the name
    label = StringField(unique=True, required=True)
    name = StringField(unique=True, required=True)
    users = ListField(ReferenceField(User))