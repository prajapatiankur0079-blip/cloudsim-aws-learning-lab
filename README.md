# CloudSim — AWS Learning & Practice Lab

A local educational simulator for learning AWS concepts without creating real AWS resources.

## Labs
- EC2, S3, VPC, NAT, Security Groups, IAM and Route 53
- Additional service simulators: Lambda, RDS, DynamoDB, EBS, CloudFront, API Gateway, CloudWatch, CloudTrail, CloudFormation, SQS, SNS, ECS, EKS, EventBridge, KMS, EFS, CodePipeline and Cost Management

## Run locally
```bash
python -m venv venv
source venv/bin/activate
pip install Flask pytest
python app.py
```

Open http://127.0.0.1:5000

## Tests
```bash
python -m pytest -q
```

## Note
CloudSim is an educational simulator, not a complete AWS emulator. It does not create real AWS resources; some additional services use generic simulation workflows.
