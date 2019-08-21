from multiprocessing import Lock, Process, Queue, current_process
import time
from datetime import datetime
import queue  # imported for using queue.Empty exception
from database import db
from modules import performancechangetracking


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
            slack_token = db.find_one('user', {'email': task['email']})['sl_accesstoken']
            if (task['type'] == 'performancechangetracking'):
                performancechangetracking(slack_token, task)

        except queue.Empty:
            break
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
                        {"status": "active"},
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


if __name__ == '__main__':
    db.init()
    while (True):
        if (datetime.now().second == 0):
            main()
            while (datetime.now().second < 1):
                pass
