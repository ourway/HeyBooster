import pymongo


class db(object):
    URI = "mongodb://ilteriskeskin:<password>@myflask-shard-00-00-raeh0.mongodb.net:27017,myflask-shard-00-01-raeh0.mongodb.net:27017,myflask-shard-00-02-raeh0.mongodb.net:27017/test?ssl=true&replicaSet=myFlask-shard-0&authSource=admin&retryWrites=true&w=majority"

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
    
    def find(collection, query):
        return db.DATABASE[collection].find(query)
    
    def find_and_modify(collection, email, **kwargs):
        print(kwargs)
        db.DATABASE[collection].find_and_modify(query={'email': email},
                                                update={"$set": kwargs}, upsert=False,
                                                full_response=True)
