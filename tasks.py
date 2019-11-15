from celery import Celery
import os
from analyticsAudit import analyticsAudit
from database import db
from bson.objectid import ObjectId


#REDIS_SERVER_SECRET = os.environ.get('REDIS_SERVER_SECRET').strip()
#REDIS_SERVER_IPADDR = os.environ.get('REDIS_SERVER_IPADDR').strip()
#REDIS_SERVER_PORT = os.environ.get('REDIS_SERVER_PORT').strip()
#REDIS_SERVER_DBNAME = os.environ.get('REDIS_SERVER_DBNAME').strip()
# Where the downloaded files will be stored
#BASEDIR="/home/app/HeyBooster"
#BROKER_URI = 'redis://:{}@{}:{}/{}'.format(REDIS_SERVER_SECRET,
#                                           REDIS_SERVER_IPADDR,
#                                           REDIS_SERVER_PORT,
#                                           REDIS_SERVER_DBNAME)
# Create the app and set the broker location (RabbitMQ)
celery_app = Celery()
celery_app.config_from_object('celeryconfig')

@celery_app.task
def run_analyticsAudit(slack_token, datasourceID):
    dataSource = db.find_one("datasource", query={"_id": ObjectId(datasourceID)})
    analyticsAudit(slack_token, task=None, dataSource=dataSource)
    return True


