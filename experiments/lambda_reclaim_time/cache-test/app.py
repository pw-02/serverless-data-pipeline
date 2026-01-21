#!/usr/bin/env python3
import aws_cdk as cdk
from cache_test_stack import CacheTestStack

app = cdk.App()
CacheTestStack(app, "CacheTestStack")
app.synth()
