import time
from apscheduler.schedulers.background import BackgroundScheduler
import main

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Schedule agent.run() every day at 09:00 local time
    scheduler.add_job(main.run_agent, 'cron', hour=9, minute=0)
    scheduler.start()
    print("Scheduler started. Running immediately as well.")
    main.run_agent()
    try:
        # Keep the process alive
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("Scheduler shut down.")

if __name__ == "__main__":
    start_scheduler()
