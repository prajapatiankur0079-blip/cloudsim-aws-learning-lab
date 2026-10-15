import ipaddress
import os
import sqlite3
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash

vpc_bp = Blueprint("vpc", __name__, url_prefix="/practice/vpc")
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloudlab.db")


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def timestamp():
    return datetime.now().strftime("%d %b %Y, %I:%M %p")


def init_vpc_db():
    conn = db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS vpcs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            cidr TEXT NOT NULL,
            igw_attached INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS vpc_subnets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vpc_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            cidr TEXT NOT NULL,
            subnet_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (vpc_id) REFERENCES vpcs(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS vpc_routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subnet_id INTEGER NOT NULL,
            destination TEXT NOT NULL,
            target TEXT NOT NULL,
            FOREIGN KEY (subnet_id) REFERENCES vpc_subnets(id) ON DELETE CASCADE,
            UNIQUE (subnet_id, destination)
        );
    """)
    conn.commit()
    conn.close()


@vpc_bp.route("/", methods=["GET"])
def dashboard():
    conn = db()
    vpcs = conn.execute("SELECT * FROM vpcs ORDER BY id DESC").fetchall()
    subnets = conn.execute("""
        SELECT s.*, v.name AS vpc_name, v.cidr AS vpc_cidr,
               v.igw_attached
        FROM vpc_subnets s
        JOIN vpcs v ON v.id = s.vpc_id
        ORDER BY s.id DESC
    """).fetchall()
    routes = conn.execute("""
        SELECT r.*, s.name AS subnet_name, v.name AS vpc_name
        FROM vpc_routes r
        JOIN vpc_subnets s ON s.id = r.subnet_id
        JOIN vpcs v ON v.id = s.vpc_id
        ORDER BY r.id DESC
    """).fetchall()
    nat_gateways = conn.execute("""
        SELECT n.*, v.name AS vpc_name,
               ps.name AS public_subnet_name, ps.cidr AS public_subnet_cidr
        FROM vpc_nat_gateways n
        JOIN vpcs v ON v.id = n.vpc_id
        JOIN vpc_subnets ps ON ps.id = n.public_subnet_id
        ORDER BY n.id DESC
    """).fetchall()
    conn.close()
    return render_template(
        "vpc.html", vpcs=vpcs, subnets=subnets, routes=routes,
        nat_gateways=nat_gateways
    )


@vpc_bp.route("/create", methods=["POST"])
def create_vpc():
    name = request.form.get("name", "").strip()
    cidr_text = request.form.get("cidr", "").strip()

    if not name or len(name) > 60:
        flash("VPC name 1–60 characters ka hona chahiye.", "error")
        return redirect(url_for("vpc.dashboard"))

    try:
        network = ipaddress.ip_network(cidr_text, strict=True)
        if network.version != 4 or not 16 <= network.prefixlen <= 28:
            raise ValueError
    except ValueError:
        flash("Valid IPv4 VPC CIDR use karo, jaise 10.0.0.0/16.", "error")
        return redirect(url_for("vpc.dashboard"))

    conn = db()
    conn.execute(
        "INSERT INTO vpcs (name, cidr, created_at) VALUES (?, ?, ?)",
        (name, str(network), timestamp())
    )
    conn.commit()
    conn.close()
    flash(f"Simulated VPC '{name}' create ho gaya.", "success")
    return redirect(url_for("vpc.dashboard"))


@vpc_bp.route("/subnet/create", methods=["POST"])
def create_subnet():
    vpc_id = request.form.get("vpc_id", type=int)
    name = request.form.get("name", "").strip()
    cidr_text = request.form.get("cidr", "").strip()
    subnet_type = request.form.get("subnet_type", "public")

    if not name or len(name) > 60 or subnet_type not in ("public", "private"):
        flash("Subnet name aur type check karo.", "error")
        return redirect(url_for("vpc.dashboard"))

    try:
        network = ipaddress.ip_network(cidr_text, strict=True)
        if network.version != 4 or network.prefixlen < 16 or network.prefixlen > 28:
            raise ValueError
    except ValueError:
        flash("Valid subnet CIDR use karo, jaise 10.0.1.0/24.", "error")
        return redirect(url_for("vpc.dashboard"))

    conn = db()
    vpc = conn.execute(
        "SELECT * FROM vpcs WHERE id = ?", (vpc_id,)
    ).fetchone()

    if vpc is None:
        conn.close()
        flash("Pehle ek VPC select ya create karo.", "error")
        return redirect(url_for("vpc.dashboard"))

    vpc_network = ipaddress.ip_network(vpc["cidr"])
    if not network.subnet_of(vpc_network) or network == vpc_network:
        conn.close()
        flash("Subnet CIDR VPC ke address range ke andar hona chahiye.", "error")
        return redirect(url_for("vpc.dashboard"))

    existing = conn.execute(
        "SELECT cidr FROM vpc_subnets WHERE vpc_id = ?", (vpc_id,)
    ).fetchall()

    if any(network.overlaps(ipaddress.ip_network(row["cidr"])) for row in existing):
        conn.close()
        flash("Subnet CIDR existing subnet se overlap karta hai.", "error")
        return redirect(url_for("vpc.dashboard"))

    conn.execute("""
        INSERT INTO vpc_subnets (vpc_id, name, cidr, subnet_type, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (vpc_id, name, str(network), subnet_type, timestamp()))
    conn.commit()

    subnet_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    if subnet_type == "public" and vpc["igw_attached"]:
        conn.execute("""
            INSERT OR IGNORE INTO vpc_routes (subnet_id, destination, target)
            VALUES (?, '0.0.0.0/0', 'igw')
        """, (subnet_id,))
    conn.commit()
    conn.close()

    flash(f"Subnet '{name}' create ho gaya.", "success")
    return redirect(url_for("vpc.dashboard"))


@vpc_bp.route("/<int:vpc_id>/internet-gateway", methods=["POST"])
def toggle_igw(vpc_id):
    action = request.form.get("action")
    if action not in ("attach", "detach"):
        flash("Invalid Internet Gateway action.", "error")
        return redirect(url_for("vpc.dashboard"))

    conn = db()
    vpc = conn.execute(
        "SELECT * FROM vpcs WHERE id = ?", (vpc_id,)
    ).fetchone()

    if vpc is None:
        conn.close()
        flash("VPC nahi mila.", "error")
        return redirect(url_for("vpc.dashboard"))

    attached = 1 if action == "attach" else 0
    conn.execute(
        "UPDATE vpcs SET igw_attached = ? WHERE id = ?",
        (attached, vpc_id)
    )

    if attached:
        conn.execute("""
            INSERT OR IGNORE INTO vpc_routes (subnet_id, destination, target)
            SELECT id, '0.0.0.0/0', 'igw'
            FROM vpc_subnets
            WHERE vpc_id = ? AND subnet_type = 'public'
        """, (vpc_id,))
        message = "Internet Gateway attach hua; public subnet routes update hue."
    else:
        conn.execute("""
            DELETE FROM vpc_routes
            WHERE target = 'igw'
              AND subnet_id IN (
                  SELECT id FROM vpc_subnets WHERE vpc_id = ?
              )
        """, (vpc_id,))
        message = "Internet Gateway detach hua; IGW routes remove hue."

    conn.commit()
    conn.close()
    flash(message, "success")
    return redirect(url_for("vpc.dashboard"))


@vpc_bp.route("/nat/create", methods=["POST"])
def create_nat_gateway():
    public_subnet_id = request.form.get("public_subnet_id", type=int)
    name = request.form.get("name", "").strip()

    if not name or len(name) > 60:
        flash("NAT Gateway name 1–60 characters ka hona chahiye.", "error")
        return redirect(url_for("vpc.dashboard"))

    conn = db()
    subnet = conn.execute("""
        SELECT s.*, v.igw_attached
        FROM vpc_subnets s
        JOIN vpcs v ON v.id = s.vpc_id
        WHERE s.id = ?
    """, (public_subnet_id,)).fetchone()

    if subnet is None or subnet["subnet_type"] != "public":
        conn.close()
        flash("NAT Gateway ke liye valid public subnet select karo.", "error")
        return redirect(url_for("vpc.dashboard"))

    igw_route = conn.execute("""
        SELECT id FROM vpc_routes
        WHERE subnet_id = ? AND destination = '0.0.0.0/0'
          AND target = 'igw'
    """, (public_subnet_id,)).fetchone()

    if not subnet["igw_attached"] or igw_route is None:
        conn.close()
        flash("Pehle VPC ka IGW attach karo aur public subnet ka IGW route verify karo.", "error")
        return redirect(url_for("vpc.dashboard"))

    existing = conn.execute(
        "SELECT id FROM vpc_nat_gateways WHERE vpc_id = ?",
        (subnet["vpc_id"],)
    ).fetchone()

    if existing:
        conn.close()
        flash("Is VPC mein NAT Gateway pehle se hai.", "error")
        return redirect(url_for("vpc.dashboard"))

    conn.execute("""
        INSERT INTO vpc_nat_gateways
            (vpc_id, public_subnet_id, name, created_at)
        VALUES (?, ?, ?, ?)
    """, (subnet["vpc_id"], public_subnet_id, name, timestamp()))
    conn.commit()
    conn.close()

    flash(f"Simulated NAT Gateway '{name}' create ho gaya.", "success")
    return redirect(url_for("vpc.dashboard"))


@vpc_bp.route("/nat/route", methods=["POST"])
def set_nat_route():
    subnet_id = request.form.get("subnet_id", type=int)
    conn = db()

    subnet = conn.execute("""
        SELECT s.*, v.igw_attached
        FROM vpc_subnets s
        JOIN vpcs v ON v.id = s.vpc_id
        WHERE s.id = ?
    """, (subnet_id,)).fetchone()

    if subnet is None or subnet["subnet_type"] != "private":
        conn.close()
        flash("NAT route ke liye valid private subnet select karo.", "error")
        return redirect(url_for("vpc.dashboard"))

    nat_path = conn.execute("""
        SELECT n.id
        FROM vpc_nat_gateways n
        JOIN vpc_subnets ps ON ps.id = n.public_subnet_id
        JOIN vpcs v ON v.id = n.vpc_id
        JOIN vpc_routes r ON r.subnet_id = ps.id
          AND r.destination = '0.0.0.0/0' AND r.target = 'igw'
        WHERE n.vpc_id = ? AND ps.subnet_type = 'public'
          AND v.igw_attached = 1
    """, (subnet["vpc_id"],)).fetchone()

    if nat_path is None:
        conn.close()
        flash("Is VPC mein working NAT Gateway aur public IGW route required hai.", "error")
        return redirect(url_for("vpc.dashboard"))

    conn.execute("""
        INSERT INTO vpc_routes (subnet_id, destination, target)
        VALUES (?, '0.0.0.0/0', 'nat')
        ON CONFLICT(subnet_id, destination)
        DO UPDATE SET target = 'nat'
    """, (subnet_id,))
    conn.commit()
    conn.close()

    flash(f"Private subnet '{subnet['name']}' ka default route NAT par set ho gaya.", "success")
    return redirect(url_for("vpc.dashboard"))


@vpc_bp.route("/connectivity-test", methods=["POST"])
def connectivity_test():
    subnet_id = request.form.get("subnet_id", type=int)
    destination = request.form.get("destination", "").strip()

    try:
        dest_ip = ipaddress.ip_address(destination)
    except ValueError:
        flash("Destination mein valid IP address do, jaise 8.8.8.8.", "error")
        return redirect(url_for("vpc.dashboard"))

    conn = db()
    subnet = conn.execute("""
        SELECT s.*, v.igw_attached
        FROM vpc_subnets s
        JOIN vpcs v ON v.id = s.vpc_id
        WHERE s.id = ?
    """, (subnet_id,)).fetchone()

    if subnet is None:
        conn.close()
        flash("Test ke liye valid subnet select karo.", "error")
        return redirect(url_for("vpc.dashboard"))

    route = conn.execute("""
        SELECT target FROM vpc_routes
        WHERE subnet_id = ? AND destination = '0.0.0.0/0'
    """, (subnet_id,)).fetchone()

    nat_path = conn.execute("""
        SELECT n.id
        FROM vpc_nat_gateways n
        JOIN vpc_subnets ps ON ps.id = n.public_subnet_id
        JOIN vpcs v ON v.id = n.vpc_id
        JOIN vpc_routes pr ON pr.subnet_id = ps.id
          AND pr.destination = '0.0.0.0/0' AND pr.target = 'igw'
        WHERE n.vpc_id = ? AND ps.subnet_type = 'public'
          AND v.igw_attached = 1
    """, (subnet["vpc_id"],)).fetchone()
    conn.close()

    public_allowed = (
        subnet["subnet_type"] == "public"
        and subnet["igw_attached"] == 1
        and route is not None
        and route["target"] == "igw"
        and dest_ip.is_global
    )
    private_allowed = (
        subnet["subnet_type"] == "private"
        and subnet["igw_attached"] == 1
        and route is not None
        and route["target"] == "nat"
        and nat_path is not None
        and dest_ip.is_global
    )

    if public_allowed or private_allowed:
        path = "NAT Gateway ke through" if private_allowed else "IGW ke through"
        flash(
            f"SIMULATED PASS: {subnet['name']} se {destination} tak {path} outbound route available hai.",
            "success"
        )
    else:
        flash(
            f"SIMULATED BLOCK: {subnet['name']} se {destination} tak valid internet route available nahi hai.",
            "error"
        )

    return redirect(url_for("vpc.dashboard"))


def init_nat_db():
    conn = db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vpc_nat_gateways (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vpc_id INTEGER NOT NULL UNIQUE,
            public_subnet_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (vpc_id) REFERENCES vpcs(id) ON DELETE CASCADE,
            FOREIGN KEY (public_subnet_id) REFERENCES vpc_subnets(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()
