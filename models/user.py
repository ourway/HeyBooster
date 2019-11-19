from database import db
 
class User(object):
    def __init__(self, name, firstname, lastname, email, password):
        self.name = name
        self.firstname = firstname
        self.lastname = lastname
        self.email = email
        self.password = password
        self.ga_accesstoken = ''
        self.ga_refreshtoken = ''
        self.sl_accesstoken = ''
    def insert(self):
        if not db.find_one('user', {'email': self.email}):
            db.insert(collection='user', data=self.json())
    def json(self):
        return {
                "name": self.name,
                "firstname": self.firstname,
                "lastname": self.lastname,
                "email": self.email,
                "password": self.password,
                "ga_accesstoken": self.ga_accesstoken,
                "ga_refreshtoken": self.ga_refreshtoken,
                "sl_accesstoken": self.sl_accesstoken
                }
