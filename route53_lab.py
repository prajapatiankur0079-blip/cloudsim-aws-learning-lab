
import ipaddress
import os
import re
import sqlite3
from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)

route53_bp = Blueprint(
    "route53",
    __name__,
    url_prefix="/practice/route53",
)

DB = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "cloudlab.db",
)


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def timestamp():
    return datetime.now().strftime("%d %b %Y, %I:%M %p")


def valid_domain(domain):
    domain = domain.rstrip(".")

    if not domain or len(domain) > 253:
        return False

    labels = domain.split(".")

    if len(labels) < 2:
        return False

    return all(
        len(label) <= 63
        and re.fullmatch(
            r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?",
            label,
        )
        for label in labels
    )


def valid_record_name(name, zone_domain):
    name = name.strip().lower().rstrip(".")

    if name == "@":
        return True

    if not valid_domain(name):
        return False

    return name == zone_domain or name.endswith("." + zone_domain)


def init_route53_db():
    conn = db()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS hosted_zones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL UNIQUE COLLATE NOCASE,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS dns_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_id INTEGER NOT NULL,
            record_name TEXT NOT NULL,
            record_type TEXT NOT NULL,
            record_value TEXT NOT NULL,
            ttl INTEGER NOT NULL DEFAULT 300,
            created_at TEXT NOT NULL,
            FOREIGN KEY(zone_id)
                REFERENCES hosted_zones(id)
                ON DELETE CASCADE
        );
    """)

    conn.commit()
    conn.close()


@route53_bp.route("/")
def dashboard():
    search = request.args.get("q", "").strip().lower()

    conn = db()

    zones = conn.execute("""
        SELECT *
        FROM hosted_zones
        ORDER BY id DESC
    """).fetchall()

    if search:
        records = conn.execute("""
            SELECT r.*, z.domain AS zone_domain
            FROM dns_records r
            JOIN hosted_zones z ON z.id = r.zone_id
            WHERE lower(r.record_name) LIKE ?
               OR lower(r.record_value) LIKE ?
               OR lower(z.domain) LIKE ?
            ORDER BY r.id DESC
        """, (f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
    else:
        records = conn.execute("""
            SELECT r.*, z.domain AS zone_domain
            FROM dns_records r
            JOIN hosted_zones z ON z.id = r.zone_id
            ORDER BY r.id DESC
        """).fetchall()

    conn.close()

    return render_template(
        "route53.html",
        zones=zones,
        records=records,
        search=search,
    )


@route53_bp.route("/zone/create", methods=["POST"])
def create_zone():
    domain = (
        request.form.get("domain", "")
        .strip()
        .lower()
        .rstrip(".")
    )

    if not valid_domain(domain):
        flash("Enter a valid domain, e.g. example.com.", "error")
        return redirect(url_for("route53.dashboard"))

    conn = db()

    try:
        conn.execute("""
            INSERT INTO hosted_zones (domain, created_at)
            VALUES (?, ?)
        """, (domain, timestamp()))

        conn.commit()
        flash(f"Hosted zone '{domain}' created.", "success")

    except sqlite3.IntegrityError:
        flash("This hosted zone already exists.", "error")

    finally:
        conn.close()

    return redirect(url_for("route53.dashboard"))


@route53_bp.route("/zone/<int:zone_id>/delete", methods=["POST"])
def delete_zone(zone_id):
    conn = db()

    zone = conn.execute(
        "SELECT domain FROM hosted_zones WHERE id = ?",
        (zone_id,),
    ).fetchone()

    if zone is None:
        conn.close()
        flash("Hosted zone not found.", "error")
        return redirect(url_for("route53.dashboard"))

    conn.execute(
        "DELETE FROM hosted_zones WHERE id = ?",
        (zone_id,),
    )

    conn.commit()
    conn.close()

    flash(
        f"Hosted zone '{zone['domain']}' and its records deleted.",
        "success",
    )

    return redirect(url_for("route53.dashboard"))


@route53_bp.route("/record/create", methods=["POST"])
def create_record():
    raw_zone_id = request.form.get("zone_id", "").strip()
    record_name = (
        request.form.get("record_name", "")
        .strip()
        .lower()
        .rstrip(".")
    )
    record_type = request.form.get("record_type", "").strip().upper()
    record_value = request.form.get("record_value", "").strip()
    raw_ttl = request.form.get("ttl", "300").strip()

    try:
        zone_id = int(raw_zone_id)
        ttl = int(raw_ttl)
    except ValueError:
        flash("Select a valid hosted zone and numeric TTL.", "error")
        return redirect(url_for("route53.dashboard"))

    if record_type not in {"A", "CNAME", "MX", "TXT"}:
        flash("Supported record types: A, CNAME, MX and TXT.", "error")
        return redirect(url_for("route53.dashboard"))

    if not record_name or not record_value:
        flash("Record name and value are required.", "error")
        return redirect(url_for("route53.dashboard"))

    if not 1 <= ttl <= 2147483647:
        flash("TTL must be a positive integer.", "error")
        return redirect(url_for("route53.dashboard"))

    conn = db()

    zone = conn.execute(
        "SELECT * FROM hosted_zones WHERE id = ?",
        (zone_id,),
    ).fetchone()

    if zone is None:
        conn.close()
        flash("Selected hosted zone does not exist.", "error")
        return redirect(url_for("route53.dashboard"))

    if not valid_record_name(record_name, zone["domain"]):
        conn.close()
        flash(
            "Record name must be @ or a valid name inside the selected zone.",
            "error",
        )
        return redirect(url_for("route53.dashboard"))

    if record_type == "A":
        try:
            address = ipaddress.ip_address(record_value)
            if address.version != 4:
                raise ValueError
        except ValueError:
            conn.close()
            flash("An A record requires a valid IPv4 address.", "error")
            return redirect(url_for("route53.dashboard"))

    elif record_type == "CNAME":
        target = record_value.rstrip(".")
        if not valid_domain(target):
            conn.close()
            flash("CNAME value must be a valid target domain.", "error")
            return redirect(url_for("route53.dashboard"))
        record_value = target.lower()

    elif record_type == "MX":
        parts = record_value.split()

        if (
            len(parts) != 2
            or not parts[0].isdigit()
            or not 0 <= int(parts[0]) <= 65535
            or not valid_domain(parts[1].rstrip("."))
        ):
            conn.close()
            flash(
                "MX value format: priority mail.example.com",
                "error",
            )
            return redirect(url_for("route53.dashboard"))

        record_value = f"{int(parts[0])} {parts[1].rstrip('.').lower()}"

    elif record_type == "TXT":
        if len(record_value) > 1000:
            conn.close()
            flash("TXT value must be 1000 characters or fewer.", "error")
            return redirect(url_for("route53.dashboard"))

    normalized_name = (
        zone["domain"]
        if record_name == "@"
        else record_name
    )

    existing = conn.execute("""
        SELECT record_type
        FROM dns_records
        WHERE zone_id = ? AND lower(record_name) = lower(?)
    """, (zone_id, normalized_name)).fetchall()

    if record_type == "CNAME" and existing:
        conn.close()
        flash(
            "CNAME cannot coexist with other records at the same name.",
            "error",
        )
        return redirect(url_for("route53.dashboard"))

    if record_type != "CNAME" and any(
        row["record_type"] == "CNAME" for row in existing
    ):
        conn.close()
        flash(
            "This name already has a CNAME record; remove it first.",
            "error",
        )
        return redirect(url_for("route53.dashboard"))

    duplicate = conn.execute("""
        SELECT id
        FROM dns_records
        WHERE zone_id = ?
          AND lower(record_name) = lower(?)
          AND record_type = ?
          AND record_value = ?
    """, (
        zone_id,
        normalized_name,
        record_type,
        record_value,
    )).fetchone()

    if duplicate:
        conn.close()
        flash("This DNS record already exists.", "error")
        return redirect(url_for("route53.dashboard"))

    conn.execute("""
        INSERT INTO dns_records (
            zone_id, record_name, record_type,
            record_value, ttl, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        zone_id,
        normalized_name,
        record_type,
        record_value,
        ttl,
        timestamp(),
    ))

    conn.commit()
    conn.close()

    flash(f"{record_type} record created successfully.", "success")
    return redirect(url_for("route53.dashboard"))


@route53_bp.route("/record/<int:record_id>/delete", methods=["POST"])
def delete_record(record_id):
    conn = db()

    record = conn.execute(
        "SELECT id FROM dns_records WHERE id = ?",
        (record_id,),
    ).fetchone()

    if record is None:
        conn.close()
        flash("DNS record not found.", "error")
        return redirect(url_for("route53.dashboard"))

    conn.execute(
        "DELETE FROM dns_records WHERE id = ?",
        (record_id,),
    )

    conn.commit()
    conn.close()

    flash("DNS record deleted.", "success")
    return redirect(url_for("route53.dashboard"))


@route53_bp.route("/lookup", methods=["GET"])
def lookup():
    query = request.args.get("domain", "").strip().lower().rstrip(".")

    if not query:
        flash("Enter a domain or record name to look up.", "error")
        return redirect(url_for("route53.dashboard"))

    conn = db()

    records = conn.execute("""
        SELECT r.*, z.domain AS zone_domain
        FROM dns_records r
        JOIN hosted_zones z ON z.id = r.zone_id
        WHERE lower(z.domain) = ?
           OR lower(r.record_name) = ?
        ORDER BY r.record_type, r.id
    """, (query, query)).fetchall()

    conn.close()

    if records:
        flash(f"Found {len(records)} matching DNS record(s).", "success")
    else:
        flash("No matching records found in this simulator.", "error")

    return render_template(
        "route53_lookup.html",
        query=query,
        records=records,
    )
