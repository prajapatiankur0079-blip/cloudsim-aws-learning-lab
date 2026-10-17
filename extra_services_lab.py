import json
import sqlite3
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash

extra_services_bp = Blueprint("extra_services", __name__)
DB = "cloudlab.db"


SERVICES = {
    "lambda": ("AWS Lambda", "Create functions and simulate event-driven executions.", "Run function"),
    "rds": ("Amazon RDS", "Create a database instance and simulate start, stop and backup.", "Run database action"),
    "dynamo": ("Amazon DynamoDB", "Create NoSQL tables and simulate item operations.", "Put / read item"),
    "ebs": ("Amazon EBS", "Create block volumes and simulate snapshots and attachment.", "Create snapshot"),
    "cloudfront": ("Amazon CloudFront", "Create distributions and simulate cache invalidation.", "Invalidate cache"),
    "api": ("Amazon API Gateway", "Create API endpoints and simulate test requests.", "Test endpoint"),
    "cloudwatch": ("Amazon CloudWatch", "Record simulated metrics and evaluate a threshold.", "Evaluate alarm"),
    "cloudtrail": ("AWS CloudTrail", "Inspect activity recorded by this local simulator.", "Refresh audit"),
    "cfn": ("AWS CloudFormation", "Create stacks and simulate stack deployment.", "Deploy stack"),
    "sqs": ("Amazon SQS", "Create queues and simulate sending and receiving messages.", "Process message"),
    "sns": ("Amazon SNS", "Create topics and simulate publishing notifications.", "Publish notification"),
    "ecs": ("Amazon ECS", "Create services and simulate container task deployments.", "Deploy tasks"),
    "eks": ("Amazon EKS", "Create cluster records and simulate workload deployment.", "Deploy workload"),
    "events": ("Amazon EventBridge", "Create event rules and simulate event delivery.", "Send test event"),
    "kms": ("AWS KMS", "Create simulated key records and practise encryption actions.", "Simulate encrypt"),
    "efs": ("Amazon EFS", "Create shared file-system records and simulate mount checks.", "Check mount"),
    "pipeline": ("AWS CodePipeline", "Create pipelines and simulate build/test/deploy stages.", "Run pipeline"),
    "cost": ("AWS Budgets & Cost", "Create local budget targets and simulate spending checks.", "Check budget"),
}

def connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def stamp():
    return datetime.now().strftime("%d %b %Y, %I:%M %p")

def init_extra_services_db():
    conn = connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS extra_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service TEXT NOT NULL,
            name TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            state TEXT NOT NULL DEFAULT 'created',
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS extra_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service TEXT NOT NULL,
            resource_name TEXT NOT NULL,
            event TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def record_event(conn, service, resource_name, event):
    conn.execute(
        "INSERT INTO extra_events(service, resource_name, event, created_at) VALUES (?, ?, ?, ?)",
        (service, resource_name, event, stamp())
    )

@extra_services_bp.route("/practice/<service>", methods=["GET", "POST"])
def dashboard(service):
    if service not in SERVICES:
        return "Service lab not found", 404

    title, description, action_label = SERVICES[service]
    conn = connect()

    if request.method == "POST":
        operation = request.form.get("operation", "")
        name = request.form.get("name", "").strip()[:100]
        details = request.form.get("details", "").strip()[:2000]
        resource_id = request.form.get("resource_id", type=int)

        if operation == "create":
            if not name:
                flash("Resource name is required.", "error")
            else:
                conn.execute(
                    "INSERT INTO extra_resources(service, name, details, state, created_at) VALUES (?, ?, ?, ?, ?)",
                    (service, name, details, "created", stamp())
                )
                record_event(conn, service, name, "Created resource")
                flash(f"{title}: '{name}' created in local simulation.", "success")

        elif operation in ("action", "delete") and resource_id:
            resource = conn.execute(
                "SELECT * FROM extra_resources WHERE id = ? AND service = ?",
                (resource_id, service)
            ).fetchone()

            if resource:
                if operation == "delete":
                    conn.execute("DELETE FROM extra_resources WHERE id = ?", (resource_id,))
                    record_event(conn, service, resource["name"], "Deleted resource")
                    flash("Resource deleted from the local simulator.", "success")
                else:
                    action = action_label
                    state = resource["state"]
                    if service == "rds":
                        state = "stopped" if state == "available" else "available"
                    elif service == "lambda":
                        state = "executed"
                    elif service == "sqs":
                        state = "message processed"
                    elif service == "sns":
                        state = "notification published"
                    elif service == "cloudwatch":
                        state = "alarm evaluated"
                    elif service == "cloudtrail":
                        state = "audit refreshed"
                    elif service == "cfn":
                        state = "CREATE_COMPLETE"
                    elif service in ("ecs", "eks", "pipeline"):
                        state = "deployment successful"
                    elif service == "cost":
                        state = "budget checked"
                    elif service == "dynamo":
                        state = "item operation simulated"
                    elif service == "events":
                        state = "event delivered"
                    elif service == "api":
                        state = "request tested"
                    elif service == "cloudfront":
                        state = "cache invalidated"
                    elif service == "ebs":
                        state = "snapshot created"
                    elif service == "kms":
                        state = "encryption simulated"
                    elif service == "efs":
                        state = "mount check complete"

                    extra = f"\nLast operation: {action} at {stamp()}"
                    conn.execute(
                        "UPDATE extra_resources SET state = ?, details = details || ? WHERE id = ?",
                        (state, extra, resource_id)
                    )
                    record_event(conn, service, resource["name"], action)
                    flash(f"Simulation complete: {action}.", "success")

        conn.commit()
        conn.close()
        return redirect(url_for("extra_services.dashboard", service=service))

    resources = conn.execute(
        "SELECT * FROM extra_resources WHERE service = ? ORDER BY id DESC",
        (service,)
    ).fetchall()

    # Audit history is global: CloudTrail can show activity across simulator modules.
    if service == "cloudtrail":
        events = conn.execute(
            "SELECT * FROM extra_events ORDER BY id DESC LIMIT 50"
        ).fetchall()
    else:
        events = conn.execute(
            "SELECT * FROM extra_events WHERE service = ? ORDER BY id DESC LIMIT 20",
            (service,)
        ).fetchall()

    conn.close()
    return render_template(
        "extra_service.html",
        service=service,
        title=title,
        description=description,
        action_label=action_label,
        resources=resources,
        events=events,
    )
