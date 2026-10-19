import fnmatch
import os
import sqlite3
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash

iam_bp = Blueprint("iam", __name__, url_prefix="/practice/iam")
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloudlab.db")


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def timestamp():
    return datetime.now().strftime("%d %b %Y, %I:%M %p")


def init_iam_db():
    conn = db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS iam_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS iam_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS iam_user_groups (
            user_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, group_id),
            FOREIGN KEY(user_id) REFERENCES iam_users(id) ON DELETE CASCADE,
            FOREIGN KEY(group_id) REFERENCES iam_groups(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS iam_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS iam_policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            effect TEXT NOT NULL CHECK(effect IN ('Allow', 'Deny')),
            action TEXT NOT NULL,
            resource TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS iam_policy_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_id INTEGER NOT NULL,
            principal_type TEXT NOT NULL
                CHECK(principal_type IN ('user', 'group', 'role')),
            principal_id INTEGER NOT NULL,
            UNIQUE(policy_id, principal_type, principal_id),
            FOREIGN KEY(policy_id) REFERENCES iam_policies(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()


def go_home():
    return redirect(url_for("iam.dashboard"))


@iam_bp.route("/")
def dashboard():
    conn = db()
    users = conn.execute("SELECT * FROM iam_users ORDER BY id DESC").fetchall()
    groups = conn.execute("SELECT * FROM iam_groups ORDER BY id DESC").fetchall()
    roles = conn.execute("SELECT * FROM iam_roles ORDER BY id DESC").fetchall()
    policies = conn.execute("SELECT * FROM iam_policies ORDER BY id DESC").fetchall()

    memberships = conn.execute("""
        SELECT ug.user_id, ug.group_id, u.name AS user_name,
               g.name AS group_name
        FROM iam_user_groups ug
        JOIN iam_users u ON u.id = ug.user_id
        JOIN iam_groups g ON g.id = ug.group_id
        ORDER BY u.name, g.name
    """).fetchall()

    attachments = conn.execute("""
        SELECT a.id, a.principal_type, a.principal_id, p.name AS policy_name,
               CASE
                 WHEN a.principal_type = 'user'
                   THEN (SELECT name FROM iam_users WHERE id = a.principal_id)
                 WHEN a.principal_type = 'group'
                   THEN (SELECT name FROM iam_groups WHERE id = a.principal_id)
                 WHEN a.principal_type = 'role'
                   THEN (SELECT name FROM iam_roles WHERE id = a.principal_id)
               END AS principal_name
        FROM iam_policy_attachments a
        JOIN iam_policies p ON p.id = a.policy_id
        ORDER BY a.id DESC
    """).fetchall()
    conn.close()

    return render_template(
        "iam.html",
        users=users, groups=groups, roles=roles, policies=policies,
        memberships=memberships, attachments=attachments,
        result=None
    )


@iam_bp.route("/user/create", methods=["POST"])
def create_user():
    name = request.form.get("name", "").strip()
    if not name:
        flash("User name is required.", "error")
        return go_home()
    conn = db()
    try:
        conn.execute(
            "INSERT INTO iam_users (name, created_at) VALUES (?, ?)",
            (name, timestamp())
        )
        conn.commit()
        flash("IAM user created.", "success")
    except sqlite3.IntegrityError:
        flash("That user name already exists.", "error")
    finally:
        conn.close()
    return go_home()


@iam_bp.route("/user/<int:user_id>/delete", methods=["POST"])
def delete_user(user_id):
    conn = db()
    conn.execute("DELETE FROM iam_users WHERE id = ?", (user_id,))
    conn.execute(
        "DELETE FROM iam_policy_attachments WHERE principal_type='user' AND principal_id=?",
        (user_id,)
    )
    conn.commit()
    conn.close()
    flash("User deleted.", "success")
    return go_home()


@iam_bp.route("/group/create", methods=["POST"])
def create_group():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Group name is required.", "error")
        return go_home()
    conn = db()
    try:
        conn.execute(
            "INSERT INTO iam_groups (name, created_at) VALUES (?, ?)",
            (name, timestamp())
        )
        conn.commit()
        flash("IAM group created.", "success")
    except sqlite3.IntegrityError:
        flash("That group name already exists.", "error")
    finally:
        conn.close()
    return go_home()


@iam_bp.route("/group/<int:group_id>/delete", methods=["POST"])
def delete_group(group_id):
    conn = db()
    conn.execute("DELETE FROM iam_groups WHERE id = ?", (group_id,))
    conn.execute(
        "DELETE FROM iam_policy_attachments WHERE principal_type='group' AND principal_id=?",
        (group_id,)
    )
    conn.commit()
    conn.close()
    flash("Group deleted.", "success")
    return go_home()


@iam_bp.route("/membership", methods=["POST"])
def add_membership():
    try:
        user_id = int(request.form.get("user_id", ""))
        group_id = int(request.form.get("group_id", ""))
    except ValueError:
        flash("Choose a valid user and group.", "error")
        return go_home()

    conn = db()
    try:
        conn.execute(
            "INSERT INTO iam_user_groups (user_id, group_id) VALUES (?, ?)",
            (user_id, group_id)
        )
        conn.commit()
        flash("User added to group.", "success")
    except sqlite3.IntegrityError:
        flash("Membership already exists or the selection is invalid.", "error")
    finally:
        conn.close()
    return go_home()


@iam_bp.route("/membership/delete", methods=["POST"])
def delete_membership():
    try:
        user_id = int(request.form.get("user_id", ""))
        group_id = int(request.form.get("group_id", ""))
    except ValueError:
        flash("Invalid membership selection.", "error")
        return go_home()

    conn = db()
    conn.execute(
        "DELETE FROM iam_user_groups WHERE user_id=? AND group_id=?",
        (user_id, group_id)
    )
    conn.commit()
    conn.close()
    flash("User removed from group.", "success")
    return go_home()


@iam_bp.route("/role/create", methods=["POST"])
def create_role():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    if not name:
        flash("Role name is required.", "error")
        return go_home()
    conn = db()
    try:
        conn.execute(
            "INSERT INTO iam_roles (name, description, created_at) VALUES (?, ?, ?)",
            (name, description, timestamp())
        )
        conn.commit()
        flash("IAM role created.", "success")
    except sqlite3.IntegrityError:
        flash("That role name already exists.", "error")
    finally:
        conn.close()
    return go_home()


@iam_bp.route("/role/<int:role_id>/delete", methods=["POST"])
def delete_role(role_id):
    conn = db()
    conn.execute("DELETE FROM iam_roles WHERE id = ?", (role_id,))
    conn.execute(
        "DELETE FROM iam_policy_attachments WHERE principal_type='role' AND principal_id=?",
        (role_id,)
    )
    conn.commit()
    conn.close()
    flash("Role deleted.", "success")
    return go_home()


@iam_bp.route("/policy/create", methods=["POST"])
def create_policy():
    name = request.form.get("name", "").strip()
    effect = request.form.get("effect", "")
    action = request.form.get("action", "").strip()
    resource = request.form.get("resource", "").strip()

    if not name or not action or not resource or effect not in ("Allow", "Deny"):
        flash("Enter a policy name, valid effect, action and resource.", "error")
        return go_home()

    conn = db()
    try:
        conn.execute("""
            INSERT INTO iam_policies (name, effect, action, resource, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (name, effect, action, resource, timestamp()))
        conn.commit()
        flash("Policy created.", "success")
    except sqlite3.IntegrityError:
        flash("That policy name already exists.", "error")
    finally:
        conn.close()
    return go_home()


@iam_bp.route("/policy/<int:policy_id>/delete", methods=["POST"])
def delete_policy(policy_id):
    conn = db()
    conn.execute("DELETE FROM iam_policies WHERE id = ?", (policy_id,))
    conn.commit()
    conn.close()
    flash("Policy and its attachments deleted.", "success")
    return go_home()


@iam_bp.route("/policy/attach", methods=["POST"])
def attach_policy():
    try:
        policy_id = int(request.form.get("policy_id", ""))
        principal_id = int(request.form.get("principal_id", ""))
    except ValueError:
        flash("Choose a valid policy and identity.", "error")
        return go_home()

    principal_type = request.form.get("principal_type", "")
    if principal_type not in ("user", "group", "role"):
        flash("Invalid identity type.", "error")
        return go_home()

    table = {"user": "iam_users", "group": "iam_groups", "role": "iam_roles"}[
        principal_type
    ]
    conn = db()
    principal = conn.execute(
        f"SELECT id FROM {table} WHERE id = ?", (principal_id,)
    ).fetchone()
    policy = conn.execute(
        "SELECT id FROM iam_policies WHERE id = ?", (policy_id,)
    ).fetchone()

    if not principal or not policy:
        flash("Selected policy or identity does not exist.", "error")
    else:
        try:
            conn.execute("""
                INSERT INTO iam_policy_attachments
                    (policy_id, principal_type, principal_id)
                VALUES (?, ?, ?)
            """, (policy_id, principal_type, principal_id))
            conn.commit()
            flash("Policy attached.", "success")
        except sqlite3.IntegrityError:
            flash("That policy is already attached.", "error")
    conn.close()
    return go_home()


@iam_bp.route("/attachment/<int:attachment_id>/delete", methods=["POST"])
def detach_policy(attachment_id):
    conn = db()
    conn.execute("DELETE FROM iam_policy_attachments WHERE id = ?", (attachment_id,))
    conn.commit()
    conn.close()
    flash("Policy detached.", "success")
    return go_home()


@iam_bp.route("/simulate", methods=["POST"])
def simulate():
    principal_type = request.form.get("principal_type", "")
    action = request.form.get("action", "").strip()
    resource = request.form.get("resource", "").strip()

    if principal_type not in ("user", "role") or not action or not resource:
        flash("Choose a user or role and enter an action and resource.", "error")
        return go_home()

    conn = db()
    table = "iam_users" if principal_type == "user" else "iam_roles"
    principal = conn.execute(
        f"SELECT id, name FROM {table} WHERE id = ?",
        (request.form.get("principal_id", ""),)
    ).fetchone()

    if not principal:
        conn.close()
        flash("Selected user or role does not exist.", "error")
        return go_home()

    params = [principal_type, principal["id"]]
    sql = """
        SELECT p.name, p.effect, p.action, p.resource
        FROM iam_policy_attachments a
        JOIN iam_policies p ON p.id = a.policy_id
        WHERE a.principal_type = ? AND a.principal_id = ?
    """

    if principal_type == "user":
        sql += """
            UNION ALL
            SELECT p.name, p.effect, p.action, p.resource
            FROM iam_policy_attachments a
            JOIN iam_policies p ON p.id = a.policy_id
            JOIN iam_user_groups ug ON ug.group_id = a.principal_id
            WHERE a.principal_type = 'group' AND ug.user_id = ?
        """
        params.append(principal["id"])

    policies = conn.execute(sql, params).fetchall()
    conn.close()

    matching = []
    for policy in policies:
        # The policy action is the pattern; the requested action
        # must match that pattern, not the other way around.
        action_match = fnmatch.fnmatchcase(
            action.lower(), policy["action"].lower()
        )
        resource_match = fnmatch.fnmatchcase(resource, policy["resource"])
        if action_match and resource_match:
            matching.append(policy)

    denied = any(p["effect"] == "Deny" for p in matching)
    allowed = any(p["effect"] == "Allow" for p in matching)
    decision = "DENY" if denied or not allowed else "ALLOW"

    result = {
        "principal": principal["name"],
        "action": action,
        "resource": resource,
        "decision": decision,
        "reason": (
            "An explicit Deny policy takes precedence."
            if denied else
            "A matching Allow policy was found."
            if allowed else
            "No matching Allow policy was found (default deny)."
        ),
        "policies": [dict(p) for p in matching]
    }

    conn = db()
    users = conn.execute("SELECT * FROM iam_users ORDER BY id DESC").fetchall()
    groups = conn.execute("SELECT * FROM iam_groups ORDER BY id DESC").fetchall()
    roles = conn.execute("SELECT * FROM iam_roles ORDER BY id DESC").fetchall()
    policies = conn.execute("SELECT * FROM iam_policies ORDER BY id DESC").fetchall()
    memberships = conn.execute("""
        SELECT ug.user_id, ug.group_id, u.name AS user_name, g.name AS group_name
        FROM iam_user_groups ug
        JOIN iam_users u ON u.id=ug.user_id
        JOIN iam_groups g ON g.id=ug.group_id
        ORDER BY u.name, g.name
    """).fetchall()
    attachments = conn.execute("""
        SELECT a.id, a.principal_type, a.principal_id, p.name AS policy_name,
               CASE
                 WHEN a.principal_type='user'
                   THEN (SELECT name FROM iam_users WHERE id=a.principal_id)
                 WHEN a.principal_type='group'
                   THEN (SELECT name FROM iam_groups WHERE id=a.principal_id)
                 WHEN a.principal_type='role'
                   THEN (SELECT name FROM iam_roles WHERE id=a.principal_id)
               END AS principal_name
        FROM iam_policy_attachments a
        JOIN iam_policies p ON p.id=a.policy_id
        ORDER BY a.id DESC
    """).fetchall()
    conn.close()

    return render_template(
        "iam.html", users=users, groups=groups, roles=roles,
        policies=policies, memberships=memberships,
        attachments=attachments, result=result
    )
