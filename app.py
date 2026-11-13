import os
import re
import time
import io
import csv
import traceback
from datetime import datetime, timedelta, timezone
from functools import wraps
import sqlite3
import psycopg
from psycopg.rows import dict_row
from flask import Flask, render_template, request, redirect, url_for, session, Response, make_response

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "escape_game_cle_secrete_adam_2026")

DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "CyberAdam2026!")

TEMPS_TOTAL_SECONDES = 10 * 60

SERVICES_MUNICIPAUX = [
    "Accueil Castelrose",
    "Accueil hôtel de ville",
    "Adjoints & conseillers délégués",
    "Bibliothèque",
    "Cabinet du maire",
    "CCAS",
    "Communication - fêtes - associations",
    "CTM",
    "Direction générale des services",
    "Direction service technique",
    "Enfance - Petite enfance - Affaires scolaires",
    "Espace culturel",
    "Espaces verts",
    "Marchés publics & assurances",
    "Multi-accueils & jeunesse",
    "Musée",
    "Police municipale",
    "Population - Etat civil - Elections",
    "Service des sports",
    "Service Financier",
    "Service informatique",
    "Service RH",
    "Service voirie",
    "Urbanisme"
]

CODE_FINAL_CORRECT = "8361"


@app.errorhandler(500)
def handle_500(e):
    trace = traceback.format_exc()
    return f"""
    <div style="background:#0b1120;color:#fecaca;padding:30px;font-family:monospace;">
        <h2 style="color:#f87171;">Diagnostic Erreur 500 :</h2>
        <pre style="background:#1e293b;padding:20px;border-radius:8px;overflow-x:auto;color:#38bdf8;">{trace}</pre>
        <a href="/" style="color:#10b981;">Retour à l'accueil</a>
    </div>
    """, 500


def parse_seconds(val):
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).strip()
    if s.isdigit():
        return int(s)
    m = re.search(r"(\d+)\s*m\s*(\d+)\s*s", s)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    nums = re.findall(r"\d+", s)
    if len(nums) == 2:
        return int(nums[0]) * 60 + int(nums[1])
    elif len(nums) == 1:
        return int(nums[0])
    return 0


def format_seconds(sec):
    s = parse_seconds(sec)
    return f"{s // 60}m {s % 60:02d}s"


def get_db():
    if DATABASE_URL:
        uri = DATABASE_URL.strip()
        if uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql://", 1)
        conn = psycopg.connect(uri, row_factory=dict_row)
        return conn
    else:
        conn = sqlite3.connect("escape_resultats.db")
        conn.row_factory = sqlite3.Row
        return conn


def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()
        if DATABASE_URL:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS escape_scores (
                    id SERIAL PRIMARY KEY,
                    agent_nom TEXT DEFAULT 'Agent',
                    nom TEXT DEFAULT 'Agent',
                    date_jeu TEXT DEFAULT '',
                    service TEXT DEFAULT '',
                    statut TEXT DEFAULT '',
                    temps_ecoule TEXT DEFAULT '0',
                    erreurs INTEGER DEFAULT 0
                )
            """)
            cur.execute("ALTER TABLE escape_scores ADD COLUMN IF NOT EXISTS agent_nom TEXT DEFAULT 'Agent'")
            cur.execute("ALTER TABLE escape_scores ADD COLUMN IF NOT EXISTS nom TEXT DEFAULT 'Agent'")
            cur.execute("ALTER TABLE escape_scores ADD COLUMN IF NOT EXISTS date_jeu TEXT DEFAULT ''")
            cur.execute("ALTER TABLE escape_scores ADD COLUMN IF NOT EXISTS service TEXT DEFAULT ''")
            cur.execute("ALTER TABLE escape_scores ADD COLUMN IF NOT EXISTS statut TEXT DEFAULT ''")
            cur.execute("ALTER TABLE escape_scores ADD COLUMN IF NOT EXISTS temps_ecoule TEXT DEFAULT '0'")
            cur.execute("ALTER TABLE escape_scores ADD COLUMN IF NOT EXISTS erreurs INTEGER DEFAULT 0")
            try:
                cur.execute("ALTER TABLE escape_scores ALTER COLUMN agent_nom SET DEFAULT 'Agent'")
                cur.execute("ALTER TABLE escape_scores ALTER COLUMN agent_nom DROP NOT NULL")
            except Exception:
                pass
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS escape_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_nom TEXT DEFAULT 'Agent',
                    nom TEXT DEFAULT 'Agent',
                    date_jeu TEXT DEFAULT '',
                    service TEXT DEFAULT '',
                    statut TEXT DEFAULT '',
                    temps_ecoule TEXT DEFAULT '0',
                    erreurs INTEGER DEFAULT 0
                )
            """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("Erreur init_db:", e)


init_db()


def check_auth(username, password):
    return username == ADMIN_USER and password == ADMIN_PASSWORD


def authenticate():
    return Response(
        "Accès restreint — Veuillez vous authentifier.",
        401,
        {"WWW-Authenticate": 'Basic realm="Administration Escape Game"'}
    )


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


def get_temps_restant():
    debut = session.get("debut_chrono")
    if not debut:
        return TEMPS_TOTAL_SECONDES
    ecoule = int(time.time() - debut)
    restant = TEMPS_TOTAL_SECONDES - ecoule
    return max(0, restant)


def enregistrer_score(statut):
    if session.get("score_enregistre"):
        return
    nom = session.get("nom", "Agent")
    service = session.get("service", "Non renseigné")
    debut = session.get("debut_chrono", time.time())
    temps_ecoule = str(max(1, min(TEMPS_TOTAL_SECONDES, int(time.time() - debut))))
    erreurs = int(session.get("erreurs", 0))
    tz_paris = timezone(timedelta(hours=1))
    date_jeu = datetime.now(tz_paris).strftime("%d/%m/%Y %H:%M")

    conn = get_db()
    cur = conn.cursor()
    if DATABASE_URL:
        cur.execute(
            "INSERT INTO escape_scores (agent_nom, nom, date_jeu, service, statut, temps_ecoule, erreurs) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (nom, nom, date_jeu, service, statut, temps_ecoule, erreurs)
        )
    else:
        cur.execute(
            "INSERT INTO escape_scores (agent_nom, nom, date_jeu, service, statut, temps_ecoule, erreurs) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (nom, nom, date_jeu, service, statut, temps_ecoule, erreurs)
        )
    conn.commit()
    cur.close()
    conn.close()
    session["score_enregistre"] = True
    session.modified = True


@app.route("/ping")
def ping():
    return "OK", 200


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        nom = (request.form.get("nom") or request.form.get("agent_nom") or request.form.get("joueur") or "Agent").strip()
        service = request.form.get("service")
        if service:
            session.clear()
            session["joueur"] = True
            session["nom"] = nom
            session["service"] = service
            session["debut_chrono"] = time.time()
            session["erreurs"] = 0
            session["indices"] = {"1": "?", "2": "?", "3": "?", "4": "?"}
            session["score_enregistre"] = False
            session.modified = True
            return redirect(url_for("enigme1"))
    return render_template("index.html", services=SERVICES_MUNICIPAUX)


@app.route("/enigme-1", methods=["GET", "POST"])
def enigme1():
    if "joueur" not in session:
        return redirect(url_for("index"))

    feedback = None
    success = False

    if request.method == "POST":
        reponse = request.form.get("email_analyse")
        if reponse == "mail_c":
            success = True
            if "indices" not in session or not isinstance(session["indices"], dict):
                session["indices"] = {"1": "?", "2": "?", "3": "?", "4": "?"}
            session["indices"]["1"] = "8"
            session.modified = True
            feedback = "Bonne analyse ! Écrire un mot de passe sur un post-it (même caché sous un clavier) ou partager ses identifiants permet à n'importe qui d'usurper votre compte. Chaque agent doit utiliser son propre accès personnel. Retenez bien ce 1er chiffre pour le coffre final : 8."
        else:
            session["erreurs"] = session.get("erreurs", 0) + 1
            session.modified = True
            feedback = "Ce comportement respecte les bonnes pratiques de sécurité. Cherchez l'action qui expose directement un accès nominatif à des tiers."

    return render_template(
        "enigme1.html",
        feedback=feedback,
        success=success,
        temps_restant=get_temps_restant(),
        indices=session.get("indices", {"1": "?", "2": "?", "3": "?", "4": "?"})
    )


@app.route("/enigme-2", methods=["GET", "POST"])
def enigme2():
    if "joueur" not in session:
        return redirect(url_for("index"))

    feedback = None
    success = False

    if request.method == "POST":
        mdp = request.form.get("mdp_test", "").strip()
        has_len = len(mdp) >= 12
        has_upper = any(c.isupper() for c in mdp)
        has_lower = any(c.islower() for c in mdp)
        has_digit = any(c.isdigit() for c in mdp)
        has_special = any(not c.isalnum() for c in mdp)
        no_forbidden = all(mot not in mdp.lower() for mot in ["mairie", "adam", "azerty", "1234", "2026"])

        if has_len and has_upper and has_lower and has_digit and has_special and no_forbidden:
            success = True
            if "indices" not in session or not isinstance(session["indices"], dict):
                session["indices"] = {"1": "8", "2": "?", "3": "?", "4": "?"}
            session["indices"]["2"] = "3"
            session.modified = True
            feedback = "Mot de passe robuste validé ! Il combine longueur (12+ caractères), complexité et absence de mots devinables. Retenez bien ce 2e chiffre pour le coffre final : 3."
        else:
            session["erreurs"] = session.get("erreurs", 0) + 1
            session.modified = True
            manquants = []
            if not has_len:
                manquants.append("12 caractères minimum")
            if not has_upper:
                manquants.append("une majuscule")
            if not has_lower:
                manquants.append("une minuscule")
            if not has_digit:
                manquants.append("un chiffre")
            if not has_special:
                manquants.append("un caractère spécial")
            if not no_forbidden:
                manquants.append("aucun mot interdit (mairie, adam, azerty, 1234, 2026)")
            feedback = "Mot de passe insuffisant. Critère(s) manquant(s) : " + ", ".join(manquants) + "."

    return render_template(
        "enigme2.html",
        feedback=feedback,
        success=success,
        temps_restant=get_temps_restant(),
        indices=session.get("indices", {"1": "?", "2": "?", "3": "?", "4": "?"})
    )


@app.route("/enigme-3", methods=["GET", "POST"])
def enigme3():
    if "joueur" not in session:
        return redirect(url_for("index"))

    feedback = None
    success = False

    if request.method == "POST":
        reponse = request.form.get("file_analyse")
        if reponse == "file_macro":
            success = True
            if "indices" not in session or not isinstance(session["indices"], dict):
                session["indices"] = {"1": "8", "2": "3", "3": "?", "4": "?"}
            session["indices"]["3"] = "6"
            session.modified = True
            feedback = "Bien vu ! Le fichier utilise une double extension (.pdf.exe) pour se faire passer pour un document Acrobat alors qu'il s'agit en réalité d'un programme exécutable malveillant. Retenez bien ce 3e chiffre pour le coffre final : 6."
        else:
            session["erreurs"] = session.get("erreurs", 0) + 1
            session.modified = True
            feedback = "Ce fichier est un document bureautique standard sans extension exécutable. Observez attentivement la fin exacte de chaque nom de fichier."

    return render_template(
        "enigme3.html",
        feedback=feedback,
        success=success,
        temps_restant=get_temps_restant(),
        indices=session.get("indices", {"1": "?", "2": "?", "3": "?", "4": "?"})
    )


@app.route("/enigme-4", methods=["GET", "POST"])
def enigme4():
    if "joueur" not in session:
        return redirect(url_for("index"))

    feedback = None
    success = False

    if request.method == "POST":
        ordre_str = request.form.get("ordre_actions", "").strip()
        actions_choisies = [a for a in ordre_str.split(",") if a]

        if actions_choisies == ["debrancher", "prevenir"]:
            success = True
            if "indices" not in session or not isinstance(session["indices"], dict):
                session["indices"] = {"1": "8", "2": "3", "3": "6", "4": "?"}
            session["indices"]["4"] = "1"
            session.modified = True
            feedback = "Protocole d'urgence parfait et dans le bon ordre ! 1) Isoler immédiatement le poste du réseau coupe la propagation aux serveurs municipaux, et 2) Alerter la DSI par téléphone permet une intervention rapide. Retenez bien ce 4e et dernier chiffre : 1."
        elif set(actions_choisies) == {"debrancher", "prevenir"}:
            session["erreurs"] = session.get("erreurs", 0) + 1
            session.modified = True
            feedback = "Vous avez trouvé les deux bonnes actions, mais pas dans le bon ordre de priorité ! Chaque seconde compte : quelle action physique stoppe immédiatement la propagation avant même de passer un appel ?"
        else:
            session["erreurs"] = session.get("erreurs", 0) + 1
            session.modified = True
            feedback = "Sélection ou ordre incorrect. Identifiez les 2 seules actions pertinentes et cliquez dessus dans l'ordre chronologique d'urgence."

    return render_template(
        "enigme4.html",
        feedback=feedback,
        success=success,
        temps_restant=get_temps_restant(),
        indices=session.get("indices", {"1": "?", "2": "?", "3": "?", "4": "?"})
    )


@app.route("/coffre", methods=["GET", "POST"])
def coffre():
    if "joueur" not in session:
        return redirect(url_for("index"))

    indices = session.get("indices")
    if not isinstance(indices, dict):
        indices = {"1": "?", "2": "?", "3": "?", "4": "?"}

    feedback = None
    if request.method == "POST":
        code = (request.form.get("code_final") or request.form.get("code") or "").strip()
        if code == CODE_FINAL_CORRECT:
            session["score_enregistre"] = False
            enregistrer_score("Victoire (Système Débloqué)")
            return redirect(url_for("victoire"))
        else:
            session["erreurs"] = session.get("erreurs", 0) + 1
            session.modified = True
            feedback = "Code incorrect. Rassemblez vos souvenirs : saisissez dans l'ordre exact les 4 chiffres obtenus à la validation de chaque énigme."

    return render_template(
        "coffre.html",
        feedback=feedback,
        temps_restant=get_temps_restant(),
        indices=indices
    )


@app.route("/victoire")
def victoire():
    if "joueur" not in session:
        return redirect(url_for("index"))
    enregistrer_score("Victoire (Système Débloqué)")
    debut = session.get("debut_chrono", time.time())
    temps_ecoule = max(1, min(TEMPS_TOTAL_SECONDES, int(time.time() - debut)))
    return render_template(
        "victoire.html",
        service=session.get("service", "Non renseigné"),
        temps_ecoule=temps_ecoule,
        erreurs=session.get("erreurs", 0)
    )


@app.route("/admin/scores")
@requires_auth
def admin_scores():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM escape_scores ORDER BY id DESC")
    raw_rows = cur.fetchall()
    cur.close()
    conn.close()

    scores = []
    stats_srv = {}

    for r in raw_rows:
        row_dict = dict(r)
        nom_val = (
            row_dict.get("nom")
            or row_dict.get("agent_nom")
            or row_dict.get("nom_agent")
            or row_dict.get("joueur")
            or row_dict.get("participant")
            or "Agent"
        )
        date_val = (
            row_dict.get("date_jeu")
            or row_dict.get("date_passage")
            or row_dict.get("date")
            or "—"
        )
        srv_val = row_dict.get("service") or "Non renseigné"
        statut_val = row_dict.get("statut") or "Réussi"
        t_sec = parse_seconds(row_dict.get("temps_ecoule") or row_dict.get("temps"))
        err_val = parse_seconds(row_dict.get("erreurs"))

        scores.append({
            "id": row_dict.get("id"),
            "nom": nom_val,
            "date_jeu": date_val,
            "service": srv_val,
            "statut": statut_val,
            "temps_sec": t_sec,
            "temps_affichage": format_seconds(t_sec),
            "erreurs": err_val
        })

        if srv_val not in stats_srv:
            stats_srv[srv_val] = {"service": srv_val, "participants": 0, "total_erreurs": 0, "meilleur_temps": t_sec}
        stats_srv[srv_val]["participants"] += 1
        stats_srv[srv_val]["total_erreurs"] += err_val
        if t_sec > 0 and (stats_srv[srv_val]["meilleur_temps"] == 0 or t_sec < stats_srv[srv_val]["meilleur_temps"]):
            stats_srv[srv_val]["meilleur_temps"] = t_sec

    scores.sort(key=lambda x: (x["erreurs"], x["temps_sec"] if x["temps_sec"] > 0 else 999999))

    classement_services = []
    for s, data in stats_srv.items():
        moy_err = round(data["total_erreurs"] / data["participants"], 1)
        classement_services.append({
            "service": s,
            "participants": data["participants"],
            "moyenne_erreurs": moy_err,
            "meilleur_temps": data["meilleur_temps"],
            "meilleur_temps_affichage": format_seconds(data["meilleur_temps"])
        })

    classement_services.sort(key=lambda x: (x["moyenne_erreurs"], x["meilleur_temps"] if x["meilleur_temps"] > 0 else 999999))

    return render_template("admin_escape.html", scores=scores, classement_services=classement_services)


@app.route("/admin/export")
@requires_auth
def export_csv():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM escape_scores ORDER BY id DESC")
    raw_rows = cur.fetchall()
    cur.close()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["ID", "Nom et Prénom", "Service", "Statut", "Erreurs", "Temps", "Date de passage"])
    for r in raw_rows:
        d = dict(r)
        nom_val = d.get("nom") or d.get("agent_nom") or d.get("nom_agent") or d.get("joueur") or "Agent"
        date_val = d.get("date_jeu") or d.get("date_passage") or d.get("date") or ""
        t_fmt = format_seconds(d.get("temps_ecoule") or d.get("temps"))
        writer.writerow([d.get("id"), nom_val, d.get("service", ""), d.get("statut", ""), d.get("erreurs", 0), t_fmt, date_val])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=scores_escape_game_mairie.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8"
    return response


@app.route("/admin/delete/<int:score_id>", methods=["POST"])
@requires_auth
def delete_score(score_id):
    conn = get_db()
    cur = conn.cursor()
    if DATABASE_URL:
        cur.execute("DELETE FROM escape_scores WHERE id = %s", (score_id,))
    else:
        cur.execute("DELETE FROM escape_scores WHERE id = ?", (score_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("admin_scores"))


@app.route("/admin/reset", methods=["POST"])
@requires_auth
def reset_scores():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM escape_scores")
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("admin_scores"))


if __name__ == "__main__":
    app.run(debug=True)