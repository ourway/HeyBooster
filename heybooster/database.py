import pymongo
          
class db(object):
          
    URI = "mongodb://<username>:<password>@myflask-shard-00-00-raeh0.mongodb.net:27017,myflask-shard-00-01-raeh0.mongodb.net:27017,myflask-shard-00-02-raeh0.mongodb.net:27017/test?ssl=true&replicaSet=myFlask-shard-0&authSource=admin&retryWrites=true&w=majority"
          
    @staticmethod
    def init():
        client = pymongo.MongoClient(db.URI)
        db.DATABASE = client['test']                                                                                                                                   
          
    @staticmethod
    def insert(collection, data):
        db.DATABASE[collection].insert(data)
          
    @staticmethod
    def find_one(collection, query):
        return db.DATABASE[collection].find_one(query)
    def modify_gatoken(collection, email, accesstoken, refreshtoken):
        db.DATABASE[collection].find_and_modify(query={'email': email}, update={"$set": {'ga_accesstoken': accesstoken, 'ga_refreshtoken': refreshtoken}}, upsert=False, full_response= True)
    def modify_sltoken(collection, email, accesstoken):
        db.DATABASE[collection].find_and_modify(query={'email': email}, update={"$set": {'ga_accesstoken': accesstoken}}, upsert=False, full_response= True)
    