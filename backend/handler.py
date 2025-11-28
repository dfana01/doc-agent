"""AWS Lambda entry point.

This module handles Lambda invocations:
- HTTP requests via API Gateway (Mangum)
- Async job execution (self-invocation)
- Scheduled job recovery (CloudWatch Events)
"""
from mangum import Mangum

from app import app
from jobs import recover_stale_jobs, execute_job

mangum_handler = Mangum(app, lifespan="off")


def lambda_handler(event, context):
    # CloudWatch scheduled event for job recovery
    if event.get('source') == 'aws.events':
        result = recover_stale_jobs()
        return {
            'statusCode': 200,
            'body': f"Recovery complete: {result['retried']} retried, {result['failed']} failed"
        }
    
    # Async job execution (Lambda self-invocation)
    if event.get('job_execution') and event.get('job_id'):
        execute_job(event['job_id'])
        return {'statusCode': 200, 'body': 'Job executed'}
    
    # HTTP request via API Gateway
    return mangum_handler(event, context)
