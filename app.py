from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import uuid
from datetime import datetime
from vpc_lab import vpc_bp, init_vpc_db, init_nat_db
from security_group_lab import security_bp, init_security_group_db
from route53_lab import route53_bp, init_route53_db

app = Flask(__name__)
app.secret_key = "cloudlab-secret-key"
app.register_blueprint(vpc_bp)
app.register_blueprint(security_bp)
app.register_blueprint(route53_bp)
DB = "cloudlab.db"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def now():
    return datetime.now().strftime("%d %b %Y, %I:%M %p")


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS instances (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            instance_type TEXT NOT NULL DEFAULT 't3.micro',
            image TEXT NOT NULL DEFAULT 'Ubuntu Server 24.04',
            state TEXT NOT NULL DEFAULT 'running',
            region TEXT NOT NULL DEFAULT 'ap-south-1',
            created_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS s3_buckets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            region TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS s3_objects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bucket_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            content_type TEXT NOT NULL,
            size_kb INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            UNIQUE(bucket_id, name),
            FOREIGN KEY(bucket_id) REFERENCES s3_buckets(id)
        )
    """)

    conn.commit()
    conn.close()


def log_activity(message):
    conn = get_db()
    conn.execute(
        "INSERT INTO activity (message, created_at) VALUES (?, ?)",
        (message, now())
    )
    conn.commit()
    conn.close()


# ---------------- HOME ----------------

@app.route("/")
def index():
    return render_template("home.html")


# ---------------- LEARNING CENTER ----------------

@app.route("/learning")
def learning_center():
    return render_template("learning.html")


# ---------------- EC2 DASHBOARD ----------------

@app.route("/practice/ec2")
def ec2_dashboard():
    conn = get_db()

    instances = conn.execute(
        "SELECT * FROM instances ORDER BY rowid DESC"
    ).fetchall()

    activities = conn.execute(
        "SELECT * FROM activity ORDER BY id DESC LIMIT 10"
    ).fetchall()

    total = len(instances)
    running = sum(i["state"] == "running" for i in instances)
    stopped = sum(i["state"] == "stopped" for i in instances)

    conn.close()

    return render_template(
        "ec2.html",
        instances=instances,
        activities=activities,
        total=total,
        running=running,
        stopped=stopped
    )


# ---------------- CREATE EC2 INSTANCE ----------------

@app.route("/create", methods=["POST"])
def create_instance():
    name = request.form.get("name", "").strip()
    image = request.form.get("image", "Ubuntu Server 24.04")
    instance_type = request.form.get("instance_type", "t3.micro")

    if not name:
        flash("Please enter an instance name.", "error")
        return redirect(url_for("ec2_dashboard"))

    instance_id = "i-" + uuid.uuid4().hex[:8]

    conn = get_db()

    conn.execute("""
        INSERT INTO instances
        (id, name, instance_type, image, state, region, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        instance_id,
        name,
        instance_type,
        image,
        "running",
        "ap-south-1",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

    log_activity(f"Created instance {name} ({instance_id})")
    flash(f"Instance {name} launched successfully!", "success")

    return redirect(url_for("ec2_dashboard"))


# ---------------- EC2 ACTIONS ----------------

@app.route("/instance/<instance_id>/<action>", methods=["POST"])
def instance_action(instance_id, action):
    if action not in ("start", "stop", "terminate"):
        flash("Invalid action.", "error")
        return redirect(url_for("ec2_dashboard"))

    conn = get_db()

    instance = conn.execute(
        "SELECT * FROM instances WHERE id = ?",
        (instance_id,)
    ).fetchone()

    if instance is None:
        conn.close()
        flash("Instance not found.", "error")
        return redirect(url_for("ec2_dashboard"))

    name = instance["name"]

    if action == "terminate":
        conn.execute(
            "DELETE FROM instances WHERE id = ?",
            (instance_id,)
        )
        message = f"Terminated instance {name}"

    else:
        state = "running" if action == "start" else "stopped"

        conn.execute(
            "UPDATE instances SET state = ? WHERE id = ?",
            (state, instance_id)
        )

        message = f"Instance {name} is now {state}"

    conn.commit()
    conn.close()

    log_activity(message)
    flash(message, "success")

    return redirect(url_for("ec2_dashboard"))


# ---------------- S3 DASHBOARD + FILTER ----------------

@app.route("/practice/s3")
def s3_dashboard():
    selected_bucket = request.args.get("bucket", "all")

    conn = get_db()

    buckets = conn.execute(
        "SELECT * FROM s3_buckets ORDER BY id DESC"
    ).fetchall()

    if selected_bucket == "all":
        objects = conn.execute("""
            SELECT o.*, b.name AS bucket_name
            FROM s3_objects o
            JOIN s3_buckets b ON b.id = o.bucket_id
            ORDER BY o.id DESC
        """).fetchall()

    else:
        try:
            bucket_id = int(selected_bucket)
        except (ValueError, TypeError):
            bucket_id = -1

        objects = conn.execute("""
            SELECT o.*, b.name AS bucket_name
            FROM s3_objects o
            JOIN s3_buckets b ON b.id = o.bucket_id
            WHERE b.id = ?
            ORDER BY o.id DESC
        """, (bucket_id,)).fetchall()

    conn.close()

    return render_template(
        "s3.html",
        buckets=buckets,
        objects=objects,
        selected_bucket=selected_bucket
    )


# ---------------- CREATE S3 BUCKET ----------------

@app.route("/s3/bucket/create", methods=["POST"])
def s3_create_bucket():
    name = request.form.get("name", "").strip().lower()
    region = request.form.get("region", "ap-south-1")

    valid_name = (
        3 <= len(name) <= 63
        and name[0:1].isalnum()
        and name[-1:].isalnum()
        and all(c.islower() or c.isdigit() or c == "-" for c in name)
        and "--" not in name
    )

    if not valid_name:
        flash(
            "Use 3–63 characters: lowercase letters, numbers and hyphens.",
            "error"
        )
        return redirect(url_for("s3_dashboard"))

    conn = get_db()

    try:
        conn.execute("""
            INSERT INTO s3_buckets (name, region, created_at)
            VALUES (?, ?, ?)
        """, (name, region, now()))

        conn.commit()

    except sqlite3.IntegrityError:
        conn.close()
        flash("A bucket with this name already exists.", "error")
        return redirect(url_for("s3_dashboard"))

    conn.close()

    log_activity(f"Created simulated S3 bucket {name}")
    flash(f"Bucket {name} created successfully.", "success")

    return redirect(url_for("s3_dashboard"))


# ---------------- ADD S3 OBJECT METADATA ----------------

@app.route("/s3/object/upload", methods=["POST"])
def s3_upload_object():
    bucket_id = request.form.get("bucket_id", type=int)
    name = request.form.get("name", "").strip()
    content_type = request.form.get(
        "content_type", "application/octet-stream"
    )
    size_kb = request.form.get("size_kb", type=int)

    allowed_types = {
        "application/pdf",
        "text/plain",
        "image/jpeg",
        "application/json",
        "application/octet-stream"
    }

    if (
        not name
        or len(name) > 255
        or size_kb is None
        or not 0 <= size_kb <= 5000000
        or content_type not in allowed_types
    ):
        flash("Enter valid object details and size.", "error")
        return redirect(url_for("s3_dashboard"))

    conn = get_db()

    bucket = conn.execute(
        "SELECT name FROM s3_buckets WHERE id = ?",
        (bucket_id,)
    ).fetchone()

    if bucket is None:
        conn.close()
        flash("Select an existing bucket.", "error")
        return redirect(url_for("s3_dashboard"))

    try:
        conn.execute("""
            INSERT INTO s3_objects
            (bucket_id, name, content_type, size_kb, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            bucket_id,
            name,
            content_type,
            size_kb,
            now()
        ))

        conn.commit()

    except sqlite3.IntegrityError:
        conn.close()
        flash(
            "An object with this name already exists in that bucket.",
            "error"
        )
        return redirect(url_for("s3_dashboard"))

    conn.close()

    log_activity(
        f"Added simulated object {name} to bucket {bucket['name']}"
    )

    flash(
        "Object metadata added. No actual file was uploaded.",
        "success"
    )

    return redirect(url_for("s3_dashboard"))


# ---------------- DELETE S3 OBJECT ----------------

@app.route("/s3/object/<int:object_id>/delete", methods=["POST"])
def s3_delete_object(object_id):
    conn = get_db()

    obj = conn.execute(
        "SELECT name FROM s3_objects WHERE id = ?",
        (object_id,)
    ).fetchone()

    if obj is None:
        conn.close()
        flash("Object not found.", "error")
        return redirect(url_for("s3_dashboard"))

    conn.execute(
        "DELETE FROM s3_objects WHERE id = ?",
        (object_id,)
    )

    conn.commit()
    conn.close()

    log_activity(f"Deleted simulated S3 object {obj['name']}")
    flash("Object deleted.", "success")

    return redirect(url_for("s3_dashboard"))


# ---------------- DELETE S3 BUCKET ----------------

@app.route("/s3/bucket/<int:bucket_id>/delete", methods=["POST"])
def s3_delete_bucket(bucket_id):
    conn = get_db()

    bucket = conn.execute(
        "SELECT name FROM s3_buckets WHERE id = ?",
        (bucket_id,)
    ).fetchone()

    if bucket is None:
        conn.close()
        flash("Bucket not found.", "error")
        return redirect(url_for("s3_dashboard"))

    count = conn.execute(
        "SELECT COUNT(*) FROM s3_objects WHERE bucket_id = ?",
        (bucket_id,)
    ).fetchone()[0]

    if count:
        conn.close()
        flash("Delete all objects in this bucket first.", "error")
        return redirect(url_for("s3_dashboard"))

    conn.execute(
        "DELETE FROM s3_buckets WHERE id = ?",
        (bucket_id,)
    )

    conn.commit()
    conn.close()

    log_activity(f"Deleted simulated S3 bucket {bucket['name']}")
    flash("Bucket deleted.", "success")

    return redirect(url_for("s3_dashboard"))


# ---------------- START APPLICATION ----------------

init_db()
init_vpc_db()
init_nat_db()
init_security_group_db()
init_route53_db()
if __name__ == "__main__":
    print("CloudLab is starting...")
    app.run(host="127.0.0.1", port=5000, debug=True)
