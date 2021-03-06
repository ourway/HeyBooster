from multiprocessing import Lock, Process, Queue, current_process
import time
from datetime import datetime
import queue  # imported for using queue.Empty exception
from database import db, db2
from modules import performancechangetracking, shoppingfunnelchangetracking, costprediction, performancegoaltracking, \
    performancechangealert
from analyticsAudit import analyticsAudit, analyticsAudit_without_slack
import logging
import sys
import traceback


WAITTIME = 1
def dtimetostrf(x):
    return x.strftime('%H.%M')


def do_job(tasks_to_accomplish):
    while True:
        try:
            '''
                try to get task from the queue. get_nowait() function will 
                raise queue.Empty exception if the queue is empty. 
                queue(False) function would do the same task also.
            '''
            task = tasks_to_accomplish.get_nowait()
            logging.basicConfig(filename="orchestrator.log", filemode='a',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
            db.init()
            db2.init()
            user = db.find_one('user', {'email': task['email']})
            slack_token = user['sl_accesstoken']
            dataSource = db.find_one('datasource', query={'_id': task['datasourceID']})
            logging.info(f"User Email: {user['email']} Data Source ID: {task['datasourceID']} Task Type: {task['type']}")
            if (task['type'] == 'performancechangetracking'):
                performancechangetracking(slack_token, task, dataSource)
                db.find_and_modify('notification', query={'_id': task['_id']},
                               lastRunDate=time.time())
            elif (task['type'] == 'shoppingfunnelchangetracking'):
                shoppingfunnelchangetracking(slack_token, task, dataSource)
                db.find_and_modify('notification', query={'_id': task['_id']},
                               lastRunDate=time.time())
            elif (task['type'] == 'costprediction'):
                costprediction(slack_token, task, dataSource)
                db.find_and_modify('notification', query={'_id': task['_id']},
                               lastRunDate=time.time())
            elif (task['type'] == 'performancegoaltracking'):
                performancegoaltracking(slack_token, task, dataSource)
                db.find_and_modify('notification', query={'_id': task['_id']},
                               lastRunDate=time.time())
            elif (task['type'] == 'performancechangealert'):
                performancechangealert(slack_token, task, dataSource)
                db.find_and_modify('notification', query={'_id': task['_id']},
                               lastRunDate=time.time())
            elif task['type'] == 'analyticsAudit':
                if slack_token:
                    if "channelID" in dataSource:
                        analyticsAudit(slack_token, task, dataSource)
                    else:
                        analyticsAudit_without_slack(task, dataSource)                        
                else:
                    analyticsAudit_without_slack(task, dataSource)
            
        except queue.Empty:
            time.sleep(WAITTIME)
        except Exception as error:
            exc_type, exc_obj, exc_tb = sys.exc_info()  # this is to get error line number and description.
            file_name = [tb[0] for tb in traceback.extract_tb(exc_tb)]  # to get File Name.
            line_no = [tb[1] for tb in traceback.extract_tb(exc_tb)]  #to get Line Number
            error_type = exc_type.__name__
            error_message =  str(error)
            error_string = f"Error Type: {error_type}, Error Message: {error_message}, File Name : {file_name}, Line no : {line_no}"
            logging.error(f"TASK DID NOT RUN --- User Email: {user['email']} Data Source ID: {task['datasourceID']} Task Type: {task['type']} --- {error_string}")
    return True


def main():
    global tasks_to_accomplish
    
    mday = datetime.today().day  # Month of Day
    wday = datetime.today().weekday() + 1
    timeofDay = dtimetostrf(datetime.now())
    tasks = db.find('notification',
                    {'$and': [
                        {"timeofDay": timeofDay},
                        {"status": "1"},
                        {'$or': [
                            {"scheduleType": 'daily'},
                            {'$and': [{"scheduleType": 'weekly'}, {"frequency": wday}]},
                            {'$and': [{"scheduleType": 'monthly'}, {"frequency": mday}]}
                        ]}]})

    for task in tasks:
        tasks_to_accomplish.put(task)


if __name__ == '__main__':
    number_of_processes = 4
    tasks_to_accomplish = Queue()
    processes = []

    for w in range(number_of_processes):
            p = Process(target=do_job, args=(tasks_to_accomplish,))
            processes.append(p)
            p.start()
    logging.basicConfig(filename="orchestrator.log", filemode='a',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    db.init()
    db2.init()
    while (True):
        try:
            time.sleep(59.5 - datetime.now().second)
        except Exception as ex:
            logging.error(str(ex))
        if (datetime.now().second == 0):
            main()
