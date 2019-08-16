from database import db
 
class User(object):
    def __init__(self, name, username, email, password, ga_accesstoken, ga_refreshtoken, sl_accesstoken):
        self.name = name
        self.username = username
        self.email = email
        self.password = password
        self.ga_accesstoken = ''
        self.ga_refreshtoken = ''
        self.sl_accesstoken = ''
    def insert(self):
        if not db.find_one('user', {'username': self.username}):
            db.insert(collection='user', data=self.json())
    def json(self):
        return {
                "name": self.name,
                "username": self.username,
                "email": self.email,
                "password": self.password,
                "ga_accesstoken": self.ga_accesstoken,
                "ga_refreshtoken": self.ga_refreshtoken,
                "sl_accesstoken": self.sl_accesstoken
                }