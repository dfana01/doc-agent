"""Local development entry point.

Run with: python local.py
"""
import atexit

import uvicorn

from jobs import recover_stale_jobs

_scheduler = None


def start_scheduler():
    global _scheduler
    
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        
        _scheduler = BackgroundScheduler(daemon=True)
        _scheduler.add_job(
            recover_stale_jobs,
            'interval',
            minutes=5,
            id='job_recovery',
            name='Recover stale jobs'
        )
        _scheduler.start()
        atexit.register(lambda: _scheduler.shutdown(wait=False) if _scheduler else None)
        print("[LOCAL] Job recovery scheduler started (runs every 5 minutes)")
        
    except ImportError:
        print("[LOCAL] APScheduler not installed - job recovery disabled")


if __name__ == "__main__":
    start_scheduler()
    print("[LOCAL] Starting FastAPI development server on http://localhost:8000")
    print("[LOCAL] API docs available at http://localhost:8000/docs")
    uvicorn.run("app:app", host="localhost", port=8000, reload=True)
