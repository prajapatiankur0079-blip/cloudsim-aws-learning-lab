import ipaddress
import os
import sqlite3
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash

security_bp = Blueprint(
    "security", __name__, url_prefix="/practice/security-groups"
)
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloudlab.db")


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def timestamp():
    return datetime.now().strftime("%d %b %Y, %I:%M %p")


def init_security_group_db():
    conn = db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS security_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            vpc_id INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY(vpc_id) REFERENCES vpcs(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS security_group_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            protocol TEXT NOT NULL,
            from_port INTEGER,
            to_port INTEGER,
            source_cidr TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(group_id) REFERENCES security_groups(id)
                ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()


@security_bp.route("/")
def dashboard():
    conn = db()
    groups = conn.execute("""
        SELECT g.*, v.name AS vpc_name
        FROM security_groups g LEFT JOIN vpcs v ON v.id = g.vpc_id
        ORDER BY g.id DESC
    """).fetchall()
    rules = conn.execute("""
        SELECT r.*, g.name AS group_name
        FROM security_group_rules r
        JOIN security_groups g ON g.id = r.group_id
        ORDER BY r.id DESC
    """).fetchall()
    vpcs = conn.execute("SELECT id, name, cidr FROM vpcs ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("security_group.html", groups=groups, rules=rules, vpcs=vpcs)


@security_bp.route("/create", methods=["POST"])
def create_group():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    raw_vpc = request.form.get("vpc_id", "").strip()

    if not name or len(name) > 60 or len(description) > 200:
        flash("Group name (1-60 characters) and description (max 200) required.", "error")
        return redirect(url_for("security.dashboard"))

    try:
        vpc_id = int(raw_vpc) if raw_vpc else None
    except ValueError:
        flash("Invalid VPC selection.", "error")
        return redirect(url_for("security.dashboard"))

    conn = db()
    if vpc_id is not None and not conn.execute(
        "SELECT id FROM vpcs WHERE id=?", (vpc_id,)
    ).fetchone():
        conn.close()
        flash("Selected VPC does not exist.", "error")
        return redirect(url_for("security.dashboard"))

    conn.execute("""
        INSERT INTO security_groups(name, description, vpc_id, created_at)
        VALUES (?, ?, ?, ?)
    """, (name, description, vpc_id, timestamp()))
    conn.commit()
    conn.close()
    flash(f"Security group '{name}' created.", "success")
    return redirect(url_for("security.dashboard"))


@security_bp.route("/<int:group_id>/rule/create", methods=["POST"])
def create_rule(group_id):
    protocol = request.form.get("protocol", "").lower()
    source = request.form.get("source_cidr", "").strip()
    from_value = request.form.get("from_port", "").strip()
    to_value = request.form.get("to_port", "").strip()

    if protocol not in {"tcp", "udp", "icmp", "all"}:
        flash("Invalid protocol.", "error")
        return redirect(url_for("security.dashboard"))

    try:
        network = ipaddress.ip_network(source, strict=False)
    except ValueError:
        flash("Invalid source CIDR. Example: 203.0.113.10/32", "error")
        return redirect(url_for("security.dashboard"))

    start = end = None
    if protocol in {"tcp", "udp"}:
        try:
            start, end = int(from_value), int(to_value)
        except ValueError:
            flash("TCP/UDP rules require both ports.", "error")
            return redirect(url_for("security.dashboard"))
        if not 1 <= start <= end <= 65535:
            flash("Ports must be between 1 and 65535, with start <= end.", "error")
            return redirect(url_for("security.dashboard"))
    elif from_value or to_value:
        flash("ICMP and All protocols do not use ports in this lab.", "error")
        return redirect(url_for("security.dashboard"))

    conn = db()
    if not conn.execute(
        "SELECT id FROM security_groups WHERE id=?", (group_id,)
    ).fetchone():
        conn.close()
        flash("Security group not found.", "error")
        return redirect(url_for("security.dashboard"))

    conn.execute("""
        INSERT INTO security_group_rules
        (group_id, protocol, from_port, to_port, source_cidr, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (group_id, protocol, start, end, str(network), timestamp()))
    conn.commit()
    conn.close()
    flash("Inbound allow rule added.", "success")
    return redirect(url_for("security.dashboard"))


@security_bp.route("/rule/<int:rule_id>/delete", methods=["POST"])
def delete_rule(rule_id):
    conn = db()
    conn.execute("DELETE FROM security_group_rules WHERE id=?", (rule_id,))
    conn.commit()
    conn.close()
    flash("Rule deleted if it existed.", "success")
    return redirect(url_for("security.dashboard"))


@security_bp.route("/<int:group_id>/delete", methods=["POST"])
def delete_group(group_id):
    conn = db()
    conn.execute("DELETE FROM security_groups WHERE id=?", (group_id,))
    conn.commit()
    conn.close()
    flash("Security group deleted if it existed.", "success")
    return redirect(url_for("security.dashboard"))


@security_bp.route("/simulate", methods=["POST"])
def simulate():
    try:
        address = ipaddress.ip_address(request.form.get("source_ip", "").strip())
        group_id = int(request.form.get("group_id", ""))
        protocol = request.form.get("protocol", "").lower()
        raw_port = request.form.get("port", "").strip()
        port = int(raw_port) if raw_port else None
    except ValueError:
        flash("Enter a valid IP, group and numeric port where required.", "error")
        return redirect(url_for("security.dashboard"))

    if protocol not in {"tcp", "udp", "icmp"}:
        flash("Choose TCP, UDP or ICMP.", "error")
        return redirect(url_for("security.dashboard"))
    if protocol in {"tcp", "udp"} and (port is None or not 1 <= port <= 65535):
        flash("TCP/UDP requires a port from 1 to 65535.", "error")
        return redirect(url_for("security.dashboard"))
    if protocol == "icmp" and port is not None:
        flash("Leave port empty for ICMP.", "error")
        return redirect(url_for("security.dashboard"))

    conn = db()
    group = conn.execute(
        "SELECT * FROM security_groups WHERE id=?", (group_id,)
    ).fetchone()
    if group is None:
        conn.close()
        flash("Choose an existing group.", "error")
        return redirect(url_for("security.dashboard"))

    rules = conn.execute(
        "SELECT * FROM security_group_rules WHERE group_id=?", (group_id,)
    ).fetchall()
    conn.close()

    allowed = False
    for rule in rules:
        if rule["protocol"] not in (protocol, "all"):
            continue
        if rule["protocol"] in {"tcp", "udp"}:
            if port is None or not rule["from_port"] <= port <= rule["to_port"]:
                continue
        network = ipaddress.ip_network(rule["source_cidr"])
        if address.version == network.version and address in network:
            allowed = True
            break

    decision = "ALLOWED" if allowed else "DENIED"
    flash(
        f"Simulated traffic {decision}: {address} / {protocol.upper()} / "
        f"{port if port is not None else 'no port'} -> {group['name']}",
        "success" if allowed else "error"
    )
    return redirect(url_for("security.dashboard"))
