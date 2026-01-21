from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
)
from constructs import Construct

class CacheTestStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        code = _lambda.Code.from_asset("lambda_src")

        for i in range(200):
            fname = f"my-cache-test-{i:03d}"

            _lambda.Function(
                self,
                f"Func{i:03d}",                # CDK logical id (must be unique)
                function_name=fname,           # Actual Lambda name you invoke
                runtime=_lambda.Runtime.PYTHON_3_11,
                handler="lambda_function.handler",
                code=code,
                memory_size=1024,               # choose your config
                timeout=Duration.seconds(3),
            )
