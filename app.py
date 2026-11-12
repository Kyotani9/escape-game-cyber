import os
import time
import io
import csv
from datetime import datetime
from functools import wraps
import sqlite3
import psycopg
from psycopg.rows import dict_row
from flask import Flask, render_template, request, redirect, url_for, session, Response, make_response

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "escape_game_cle_secrete_adam_2026")

DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "D122noel")

TEMPS_TOTAL_SECONDES = 25 * 60

# Liste officielle des services municipaux
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

# Les 4 indices secrets à débloquer :
# Énigme 1 -> 8 (Analyse d'en-tête SPF/DKIM)
# Énigme 2 -> 3 (Évaluation entropie & hash)
# Énigme 3 -> 6 (Double extension masquée RTLO / macro malveillante)
# Énigme 4 -> 1 (Matrice d'isolation & confinement réseau)
CODE_FINAL_CORRECT = "8361"


def get_db():
    if DATABASE_URL:
        uri = DATABASE_URL
        if uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql://", 1)
        conn = psycopg.connect(uri)
        return conn
    else:
        conn = sqlite3.connect("escape_resultats.db")
        conn.row_factory = sqlite3.Row
        return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    if DATABASE_URL:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS escape_scores (
                id SERIAL PRIMARY KEY,
                agent_nom VARCHAR(120) NOT NULL,
                service VARCHAR(120) NOT NULL,
                statut VARCHAR(50) NOT NULL,
                erreurs INTEGER DEFAULT 0,
                temps_ecoule VARCHAR(50) NOT NULL,
                date_passage TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS escape_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_nom TEXT NOT NULL,
                service TEXT NOT NULL,
                statut TEXT NOT NULL,
                erreurs INTEGER DEFAULT 0,
                temps_ecoule TEXT NOT NULL,
                date_passage TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    conn.commit()
    conn.close()

init_db()


def check_auth(username, password):
    return username == ADMIN_USER and password == ADMIN_PASSWORD

def authenticate():
    return Response(
        "Accès refusé. Authentification DSI requise.\n", 401,
        {"WWW-Authenticate": 'Basic realm="Espace Securise Superviseur DSI"'}
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
    start = session.get("start_time")
    if not start:
        return TEMPS_TOTAL_SECONDES
    ecoule = int(time.time() - start)
    return max(0, TEMPS_TOTAL_SECONDES - ecoule)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        session.clear()
        session["joueur"] = request.form.get("joueur", "").strip() or "Agent Inconnu"
        session["service"] = request.form.get("service") or SERVICES_MUNICIPAUX[0]
        session["start_time"] = time.time()
        session["indices"] = {}
        session["erreurs"] = 0
        return redirect(url_for("enigme1"))
    return render_template("index.html", services=SERVICES_MUNICIPAUX)

@app.route("/ping")
def ping():
    return "OK", 200

# ------------------------------------------------------------------
# ÉNIGME 1 : DÉTECTION AVANCÉE SPF/DKIM & ANALYSE D'EN-TÊTE
# ------------------------------------------------------------------
@app.route("/enigme-1", methods=["GET", "POST"])
def enigme1():
    if "joueur" not in session:
        return redirect(url_for("index"))

    feedback = None
    success = False

    if request.method == "POST":
        reponse = request.form.get("email_analyse")
        # Le mail frauduleux est le C : usurpation d'adresse avec DKIM/SPF 'fail'
        if reponse == "mail_c":
            success = True
            session["indices"]["1"] = "8"
            session.modified = True
            feedback = "Excellente analyse d'en-tête ! Le faux expéditeur imitait la DGFIP mais l'en-tête technique indiquait 'SPF: FAIL' et une IP relais en Moldavie. Premier chiffre déverrouillé : 8."
        else:
            session["erreurs"] = session.get("erreurs", 0) + 1
            feedback = "Erreur ! Regardez attentivement les signatures cryptographiques SPF et DKIM dans les en-têtes bruts."

    return render_template(
        "enigme1.html",
        feedback=feedback,
        success=success,
        temps_restant=get_temps_restant(),
        indices=session.get("indices", {})
    )


# ------------------------------------------------------------------
# ÉNIGME 2 : ATTAQUE PAR DICTIONNAIRE & ROBUSTESSE
# ------------------------------------------------------------------
@app.route("/enigme-2", methods=["GET", "POST"])
def enigme2():
    if "joueur" not in session:
        return redirect(url_for("index"))

    feedback = None
    success = False

    if request.method == "POST":
        reponse = request.form.get("pass_analyse")
        # Le mot de passe B utilise une phrase de passe avec forte entropie (> 80 bits) et substitution non conventionnelle
        if reponse == "pass_b":
            success = True
            session["indices"]["2"] = "3"
            session.modified = True
            feedback = "Code validé ! La phrase de passe 'Ch@teau-Nogent*95290#Volee' possède une entropie supérieure à 85 bits, résistant aux attaques par masque et dictionnaires hybrides. Deuxième chiffre déverrouillé : 3."
        else:
            session["erreurs"] = session.get("erreurs", 0) + 1
            feedback = "Échec d'authentification ! Le mot de passe sélectionné repose sur des substitutions basiques ('a' -> '@', 'e' -> '3') vulnérables aux dictionnaires d'attaque modernes."

    return render_template(
        "enigme2.html",
        feedback=feedback,
        success=success,
        temps_restant=get_temps_restant(),
        indices=session.get("indices", {})
    )


# ------------------------------------------------------------------
# ÉNIGME 3 : CHEVAL DE TROIE, MACROS & CARACTÈRES INVISIBLES (RTLO)
# ------------------------------------------------------------------
@app.route("/enigme-3", methods=["GET", "POST"])
def enigme3():
    if "joueur" not in session:
        return redirect(url_for("index"))

    feedback = None
    success = False

    if request.method == "POST":
        reponse = request.form.get("file_analyse")
        # Le fichier piégé est le 3 : un fichier .docm avec macro auto-exécutable AutoOpen()
        if reponse == "file_macro":
            success = True
            session["indices"]["3"] = "6"
            session.modified = True
            feedback = "Piège neutralisé ! Le document contenait une macro VBA obfusquée téléchargeant une charge utile PowerShell en arrière-plan. Troisième chiffre déverrouillé : 6."
        else:
            session["erreurs"] = session.get("erreurs", 0) + 1
            feedback = "Alerte : ce document est un fichier bureautique standard sans risque d'exécution de code."

    return render_template(
        "enigme3.html",
        feedback=feedback,
        success=success,
        temps_restant=get_temps_restant(),
        indices=session.get("indices", {})
    )


# ------------------------------------------------------------------
# ÉNIGME 4 : ISOLATION DU RÉSEAU & PROCÉDURE FORENSIQUE
# ------------------------------------------------------------------
@app.route("/enigme-4", methods=["GET", "POST"])
def enigme4():
    if "joueur" not in session:
        return redirect(url_for("index"))

    feedback = None
    success = False

    if request.method == "POST":
        reponse = request.form.get("incident_action")
        # Seule la procédure 2 préserve la mémoire volatile (RAM) tout en stoppant net le mouvement latéral
        if reponse == "action_forensique":
            success = True
            session["indices"]["4"] = "1"
            session.modified = True
            feedback = "Procédure DSI exemplaire ! Déconnexion immédiate des interfaces réseau (RJ45/Wi-Fi) sans éteindre le poste pour conserver les artefacts en mémoire RAM. Quatrième chiffre déverrouillé : 1."
        else:
            session["erreurs"] = session.get("erreurs", 0) + 1
            feedback = "Procédure non conforme. Éteindre le poste supprime les données de mémoire vive indispensables à l'analyse judiciaire (artefacts RAM)."

    return render_template(
        "enigme4.html",
        feedback=feedback,
        success=success,
        temps_restant=get_temps_restant(),
        indices=session.get("indices", {})
    )


# ------------------------------------------------------------------
# TERMINAL FINAL DE DÉCHIFFREMENT & ENREGISTREMENT BDD
# ------------------------------------------------------------------
@app.route("/victoire", methods=["GET", "POST"])
def victoire():
    if "joueur" not in session:
        return redirect(url_for("index"))

    feedback = None
    reussi = False

    temps_pris = int(time.time() - session.get("start_time", time.time()))
    minutes = temps_pris // 60
    secondes = temps_pris % 60
    temps_formate = f"{minutes:02d}m {secondes:02d}s"

    if request.method == "POST":
        code = request.form.get("code_master", "").strip()
        if code == CODE_FINAL_CORRECT:
            reussi = True
            # Enregistrement en base de données
            conn = get_db()
            cursor = conn.cursor()
            query = """
                INSERT INTO escape_scores (agent_nom, service, statut, erreurs, temps_ecoule)
                VALUES (%s, %s, %s, %s, %s)
            """ if DATABASE_URL else """
                INSERT INTO escape_scores (agent_nom, service, statut, erreurs, temps_ecoule)
                VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(query, (
                session.get("joueur"),
                session.get("service"),
                "Victoire (Système Débloqué)",
                session.get("erreurs", 0),
                temps_formate
            ))
            conn.commit()
            conn.close()
        else:
            session["erreurs"] = session.get("erreurs", 0) + 1
            feedback = "Code incorrect. Assemblez les 4 chiffres dans l'ordre strict des énigmes (1 à 4)."

    return render_template(
        "victoire.html",
        feedback=feedback,
        reussi=reussi,
        temps_formate=temps_formate,
        indices=session.get("indices", {})
    )


# ------------------------------------------------------------------
# TABLEAU DE BORD ADMIN / SUPERVISEUR DSI
# ------------------------------------------------------------------
@app.route("/admin/scores")
@requires_auth
def admin_scores():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM escape_scores ORDER BY id DESC")
    scores = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM escape_scores")
    total_participants = cursor.fetchone()[0]

    cursor.execute("""
        SELECT service, COUNT(*) as nb_succes
        FROM escape_scores 
        GROUP BY service 
        ORDER BY nb_succes DESC
    """)
    stats_services = cursor.fetchall()
    conn.close()

    return render_template(
        "admin_escape.html",
        scores=scores,
        total_participants=total_participants,
        stats_services=stats_services
    )


@app.route("/admin/export-csv")
@requires_auth
def export_csv():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, agent_nom, service, statut, erreurs, temps_ecoule, date_passage FROM escape_scores ORDER BY id DESC")
    lignes = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["ID", "Nom de l'agent", "Service", "Statut", "Erreurs commises", "Temps écoulé", "Date"])

    for l in lignes:
        writer.writerow(list(l))

    reponse = make_response(output.getvalue().encode("utf-8-sig"))
    reponse.headers["Content-Disposition"] = "attachment; filename=resultats_escape_game_dsi.csv"
    reponse.headers["Content-Type"] = "text/csv; charset=utf-8"
    return reponse


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)