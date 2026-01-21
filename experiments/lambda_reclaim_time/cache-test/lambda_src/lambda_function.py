# lambda_function.py
import os
import time
import uuid

# This is set once per *execution environment* (i.e., per warm container).
# If the environment is reclaimed and recreated, this value will change.
INSTANCE_ID = str(uuid.uuid4())
FIRST_SEEN_UNIX = time.time()

def handler(event, context):
    return {
        "instance_id": INSTANCE_ID,
        "first_seen_unix": FIRST_SEEN_UNIX,
        "now_unix": time.time(),
        "aws_request_id": context.aws_request_id,
        "log_stream": context.log_stream_name,
        "memory_limit_mb": context.memory_limit_in_mb,
        "function_name": os.environ.get("AWS_LAMBDA_FUNCTION_NAME"),
    }
