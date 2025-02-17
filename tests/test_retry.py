import sched
import time
from datetime import datetime

# 创建调度器
scheduler = sched.scheduler(time.time, time.sleep)


def job(name):
    for i in range(3):
        print(datetime.now().second, name, "=>", i + 1)
        time.sleep(3)


def schedule_next_task(interval, task, name):
    print("schedule_next_task")
    task(name)
    scheduler.enter(interval, 1, schedule_next_task, (interval, task, name))


# 设置任务间隔时间（秒）
interval = 10

# 初始化并启动调度器
scheduler.enter(interval, 1, schedule_next_task, (interval, job, "job-1"))
scheduler.enter(interval, 1, schedule_next_task, (interval, job, "job-2"))
scheduler.enter(interval, 1, schedule_next_task, (interval, job, "job-3"))
# threading.Thread(target=scheduler.run).start()
scheduler.run()
