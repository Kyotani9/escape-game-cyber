import os
import time
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cle_secrete_escape_game_cyber_2026")

# Temps total imparti : 25 minutes (en secondes)
TEMPS_TOTAL_SECONDES = 25 * 60

# Le code maître à reconstituer : 7 - 4 - 9 - 2
CODE_FINAL_CORRECT = "7492"


def get_temps_restant():
    """Calcule le temps restant en secondes pour la session en cours."""
    start_time = session.get("start_time")
    if not start_time:
        return TEMPS_TOTAL_SECONDES
    ecoule = int(time.time() - start_time)
    restant = TEMPS_TOTAL_SECONDES - ecoule
    return max(0, restant)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        session.clear()
        session["joueur"] = request.form.get("joueur", "").strip() or "Agent Secret"
        session["service"] = request.form.get("service", "").strip() or "Direction Générale"
        session["start_time"] = time.time()
        session["indices"] = {}
        return redirect(url_for("enigme1"))
    return render_template("index.html")


# ------------------------------------------------------------------
# ÉNIGME 1 : HAMEÇONNAGE & SURVOL D'URL (Indice : 7)
# ------------------------------------------------------------------
@app.route("/enigme-1", methods=["GET", "POST"])
def enigme1():
    if "joueur" not in session:
        return redirect(url_for("index"))

    feedback = None
    success = False

    if request.method == "POST":
        choix = request.form.get("choix_email")
        if choix == "email_2":
            success = True
            session["indices"]["1"] = "7"
            session.modified = True
            feedback = "Analyse exacte ! L'URL cachée pointait vers un domaine malveillant (.ru). Premier chiffre déverrouillé : 7."
        else:
            feedback = "Erreur d'analyse. Ce courriel est légitime. Examinez attentivement l'adresse réelle au survol du lien."

    return render_template(
        "enigme1.html",
        feedback=feedback,
        success=success,
        temps_restant=get_temps_restant(),
        indice="7" if success else None
    )


# ------------------------------------------------------------------
# ÉNIGME 2 : ROBUSTESSE DU MOT DE PASSE (Indice : 4)
# ------------------------------------------------------------------
@app.route("/enigme-2", methods=["GET", "POST"])
def enigme2():
    if "joueur" not in session:
        return redirect(url_for("index"))

    feedback = None
    success = False

    if request.method == "POST":
        choix_mdp = request.form.get("choix_mdp")
        # Le bon mot de passe respecte les critères ANSSI/CNIL (longueur >= 12, diversité, pas d'infos persos)
        if choix_mdp == "mdp_3":
            success = True
            session["indices"]["2"] = "4"
            session.modified = True
            feedback = "Coffre déverrouillé ! Ce mot de passe est robuste (14 caractères, 4 types de caractères, sans mot du dictionnaire). Deuxième chiffre déverrouillé : 4."
        else:
            feedback = "Accès refusé ! Ce mot de passe présente une faiblesse (trop court, date prévisible ou combinaison séquentielle)."

    return render_template(
        "enigme2.html",
        feedback=feedback,
        success=success,
        temps_restant=get_temps_restant(),
        indice="4" if success else None
    )


# ------------------------------------------------------------------
# ÉNIGME 3 : DÉTECTION DU CHEVAL DE TROIE (Indice : 9)
# ------------------------------------------------------------------
@app.route("/enigme-3", methods=["GET", "POST"])
def enigme3():
    if "joueur" not in session:
        return redirect(url_for("index"))

    feedback = None
    success = False

    if request.method == "POST":
        choix_fichier = request.form.get("choix_fichier")
        # Le fichier piégé a une fausse extension double : Facture_Travaux_CTM.pdf.exe
        if choix_fichier == "fichier_piege":
            success = True
            session["indices"]["3"] = "9"
            session.modified = True
            feedback = "Menace neutralisée ! C'était un exécutable (.exe) masqué sous une fausse icône PDF. Troisième chiffre déverrouillé : 9."
        else:
            feedback = "Mauvais fichier ciblé ! Ce document est sain. Analysez scrupuleusement l'extension complète des fichiers."

    return render_template(
        "enigme3.html",
        feedback=feedback,
        success=success,
        temps_restant=get_temps_restant(),
        indice="9" if success else None
    )


# ------------------------------------------------------------------
# ÉNIGME 4 : PROCÉDURE RÉFLEXE DSI (Indice : 2)
# ------------------------------------------------------------------
@app.route("/enigme-4", methods=["GET", "POST"])
def enigme4():
    if "joueur" not in session:
        return redirect(url_for("index"))

    feedback = None
    success = False

    if request.method == "POST":
        reflexe = request.form.get("choix_reflexe")
        # Bonne pratique : isoler le poste du réseau et contacter immédiatement le service informatique
        if reflexe == "action_isoler":
            success = True
            session["indices"]["4"] = "2"
            session.modified = True
            feedback = "Protocole respecté ! Déconnecter le câble réseau / Wi-Fi coupe la propagation du rançongiciel sans éteindre le poste pour l'analyse forensique. Quatrième chiffre : 2."
        else:
            feedback = "Procédure incorrecte. Cette action risque de propager l'infection ou d'effacer les preuves volatiles en mémoire RAM."

    return render_template(
        "enigme4.html",
        feedback=feedback,
        success=success,
        temps_restant=get_temps_restant(),
        indice="2" if success else None
    )


# ------------------------------------------------------------------
# TERMINAL FINAL : DÉCHIFFREMENT DU CODE MAÎTRE
# ------------------------------------------------------------------
@app.route("/victoire", methods=["GET", "POST"])
def victoire():
    if "joueur" not in session:
        return redirect(url_for("index"))

    feedback = None
    reussi = False

    if request.method == "POST":
        code_saisi = request.form.get("code_final", "").strip()
        if code_saisi == CODE_FINAL_CORRECT:
            reussi = True
        else:
            feedback = "Code de déchiffrement invalide. Rassemblez les 4 chiffres trouvés dans les énigmes précédentes."

    temps_pris = int(time.time() - session.get("start_time", time.time()))
    minutes = temps_pris // 60
    secondes = temps_pris % 60

    return render_template(
        "victoire.html",
        feedback=feedback,
        reussi=reussi,
        temps_formate=f"{minutes:02d}m {secondes:02d}s",
        indices=session.get("indices", {})
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)