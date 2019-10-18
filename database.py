import pymongo
import os


class db(object):
    user = os.environ.get('DB_USER')
    pw = os.environ.get('DB_PASSWORD')
    URI = "mongodb://%s:%s@myflask-shard-00-00-raeh0.mongodb.net:27017,myflask-shard-00-01-raeh0.mongodb.net:27017,myflask-shard-00-02-raeh0.mongodb.net:27017/test?ssl=true&replicaSet=myFlask-shard-0&authSource=admin&retryWrites=true&w=majority" % (
        user, pw)

    @staticmethod
    def init():
        client = pymongo.MongoClient(db.URI)
        db.DATABASE = client['test']


    @staticmethod
    def insert(collection, data):
        db.DATABASE[collection].insert(data)
        
        
    def insert_one(collection, data):
        return db.DATABASE[collection].insert_one(data)


    @staticmethod
    def find_one(collection, query):
        return db.DATABASE[collection].find_one(query)


    def find(collection, query):
        return db.DATABASE[collection].find(query)


    def find_and_modify(collection, query, **kwargs):
        print(kwargs)
        db.DATABASE[collection].find_and_modify(query=query,
                                                update={"$set": kwargs}, upsert=False,
                                                full_response=True)


class db2(object):
    user = os.environ.get('DB_USER')
    pw = os.environ.get('DB_PASSWORD')
    URI = "mongodb://%s:%s@cluster0-shard-00-00-kk3ol.mongodb.net:27017,cluster0-shard-00-01-kk3ol.mongodb.net:27017,cluster0-shard-00-02-kk3ol.mongodb.net:27017/test?ssl=true&replicaSet=Cluster0-shard-0&authSource=admin&retryWrites=true&w=majority" % (
        user, pw)


    @staticmethod
    def init():
        client = pymongo.MongoClient(db2.URI)
        db2.DATABASE = client['test']


    @staticmethod
    def insert(collection, data):
        db2.DATABASE[collection].insert(data)
        
        
    def insert_one(collection, data):
        return db2.DATABASE[collection].insert_one(data)


    @staticmethod
    def find_one(collection, query):
        return db2.DATABASE[collection].find_one(query)


    def find(collection, query):
        return db2.DATABASE[collection].find(query)


    def find_and_modify(collection, query, **kwargs):
        print(kwargs)
        db2.DATABASE[collection].find_and_modify(query=query,
                                                update={"$set": kwargs}, upsert=False,
                                                full_response=True)