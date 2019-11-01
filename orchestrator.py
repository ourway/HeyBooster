from multiprocessing import Lock, Process, Queue, current_process
import time
from datetime import datetime
import queue  # imported for using queue.Empty exception
from database import db, db2
from modules import performancechangetracking, shoppingfunnelchangetracking, costprediction, performancegoaltracking, \
    performancechangealert


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
            db.init()
            db2.init()
            user = db.find_one('user', {'email': task['email']})
            slack_token = user['sl_accesstoken']
            dataSource = db.find_one('datasource', query={'_id': task['datasourceID']})
            if (task['type'] == 'performancechangetracking'):
                performancechangetracking(slack_token, task, dataSource)
            elif (task['type'] == 'shoppingfunnelchangetracking'):
                shoppingfunnelchangetracking(slack_token, task, dataSource)
            elif (task['type'] == 'costprediction'):
                costprediction(slack_token, task, dataSource)
            elif (task['type'] == 'performancegoaltracking'):
                performancegoaltracking(slack_token, task, dataSource)
            elif (task['type'] == 'performancechangealert'):
                performancechangealert(slack_token, task, dataSource)
            db.find_and_modify('notification', query={'email': task['email'], 'type': task['type']},
                               lastRunDate=time.time())
        except queue.Empty:
            break
        except Exception:
            log_write()
    return True


def main():
    number_of_processes = 4
    tasks_to_accomplish = Queue()
    processes = []

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

    # creating processes
    for w in range(number_of_processes):
        p = Process(target=do_job, args=(tasks_to_accomplish,))
        processes.append(p)
        p.start()

    # completing process
    for p in processes:
        p.join()

    return True


def log_write():
    file = open('../orchestrator_log_files', 'a')
    file.write('Orchestrator patladı {} \n'.format(datetime.today()))
    file.close()


if __name__ == '__main__':
    db.init()
    db2.init()
    while (True):
        try:
            time.sleep(59.5 - datetime.now().second)
        except Exception:
            log_write()
        if (datetime.now().second == 0):
            main()
