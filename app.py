import streamlit as st
import sqlite3
from datetime import datetime, date

st.set_page_config(
    page_title="Système de Gestion Bancaire - UPN",
    page_icon="🏦",
    layout="wide"
)


class DatabaseManager:
    def __init__(self, db_name="banque_v5.db"):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS utilisateurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT,
                email TEXT,
                date_naissance TEXT,
                lieu_naissance TEXT,
                sexe TEXT,
                adresse TEXT,
                fonction TEXT,
                client_id INTEGER,
                FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE SET NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT,
                prenom TEXT,
                date_naissance TEXT,
                lieu_naissance TEXT,
                sexe TEXT,
                email TEXT,
                telephone TEXT,
                adresse TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comptes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_compte TEXT UNIQUE,
                type_compte TEXT,
                solde_usd REAL DEFAULT 0.0,
                solde_cdf REAL DEFAULT 0.0,
                code_secret TEXT,
                client_id INTEGER,
                FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("PRAGMA table_info(comptes)")
        colonnes_comptes = [col[1] for col in cursor.fetchall()]
        if "solde_cdf" not in colonnes_comptes:
            try:
                cursor.execute("ALTER TABLE comptes ADD COLUMN solde_cdf REAL DEFAULT 0.0")
                if "solde" in colonnes_comptes and "solde_usd" not in colonnes_comptes:
                    cursor.execute("ALTER TABLE comptes RENAME COLUMN solde TO solde_usd")
            except Exception:
                pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_compte TEXT,
                type_operation TEXT,
                montant REAL,
                devise TEXT,
                date TEXT
            )
        """)

        cursor.execute("PRAGMA table_info(operations)")
        colonnes_ops = [col[1] for col in cursor.fetchall()]
        if "devise" not in colonnes_ops:
            try:
                cursor.execute("ALTER TABLE operations ADD COLUMN devise TEXT DEFAULT 'USD'")
            except Exception:
                pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS journal_securite (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                numero_compte TEXT,
                type_menace TEXT,
                description TEXT,
                date TEXT
            )
        """)

        cursor.execute("SELECT COUNT(*) FROM utilisateurs WHERE role='admin'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO utilisateurs (username, password, role, email, date_naissance, lieu_naissance, sexe, adresse, fonction) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ("admin", "admin123", "admin", "admin@banque.com", "1985-01-01", "Kinshasa", "Masculin",
                  "Avenue de l'Université", "Administrateur Système"))

        cursor.execute("SELECT COUNT(*) FROM utilisateurs WHERE role='agent'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO utilisateurs (username, password, role, email, date_naissance, lieu_naissance, sexe, adresse, fonction) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ("agent", "agent123", "agent", "agent@banque.com", "1990-01-01", "Kinshasa", "Masculin",
                  "Avenue de l'Université", "Gestionnaire de comptes"))

        conn.commit()
        conn.close()

class UserManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def creer_agent(self, username, password="agent123", email="", date_naissance="1995-01-01", lieu_naissance="",
                    sexe="Masculin", adresse="", fonction="Gestionnaire"):
        if not password:
            password = "agent123"

        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO utilisateurs (username, password, role, email, date_naissance, lieu_naissance, sexe, adresse, fonction) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (username, password, "agent", email, str(date_naissance), lieu_naissance, sexe, adresse, fonction))
            conn.commit()
            success = True
            msg = f"Agent '{username}' créé avec succès !"
        except sqlite3.IntegrityError:
            success = False
            msg = "Ce nom d'utilisateur existe déjà."
        conn.close()
        return success, msg

    def lister_agents(self):
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, email, date_naissance, lieu_naissance, sexe, adresse, fonction FROM utilisateurs WHERE role = 'agent'")
        result = cursor.fetchall()
        conn.close()
        return result

    def supprimer_agent(self, user_id):
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM utilisateurs WHERE id = ? AND role = 'agent'", (user_id,))
        conn.commit()
        conn.close()


class SecurityScanner:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def analyser_activite_suspecte(self):
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        alertes = []

        cursor.execute(
            "SELECT numero_compte, type_operation, montant, devise, date FROM operations WHERE ((devise='USD' AND montant > 5000) OR (devise='FC' AND montant > 15000000)) AND (type_operation LIKE '%Retrait%' OR type_operation LIKE '%Débit%')")
        for op in cursor.fetchall():
            alertes.append({
                "niveau": "⚠️ ATTENTION",
                "type": "Opération financière lourde",
                "description": f"Compte {op[0]} : {op[1]} de {op[2]:,.2f} {op[3]} effectué le {op[4]}"
            })

        cursor.execute("SELECT numero_compte, solde_usd, solde_cdf FROM comptes WHERE solde_usd < 0 OR solde_cdf < 0")
        for s in cursor.fetchall():
            if s[1] < 0:
                alertes.append({"niveau": "🚨 CRITIQUE", "type": "Solde négatif",
                                "description": f"Le compte {s[0]} a un solde USD négatif ({s[1]:,.2f} $)"})
            if s[2] < 0:
                alertes.append({"niveau": "🚨 CRITIQUE", "type": "Solde négatif",
                                "description": f"Le compte {s[0]} a un solde CDF négatif ({s[2]:,.2f} FC)"})

        conn.close()
        return alertes

class Client:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def calculer_age(self, date_naissance_str):
        date_naiss = datetime.strptime(date_naissance_str, "%Y-%m-%d").date()
        today = date.today()
        age = today.year - date_naiss.year - ((today.month, today.day) < (date_naiss.month, date_naiss.day))
        return age

    def ajouter(self, nom, prenom, date_naissance, lieu_naissance, sexe, email, telephone, adresse, username,
                password_connexion):
        age = self.calculer_age(str(date_naissance))
        if age < 18:
            return False, f"Âge requis non atteint ({age} ans). Le client doit avoir au moins 18 ans."

        if not username:
            return False, "Le nom d'utilisateur (username) est obligatoire."

        if not password_connexion:
            return False, "Le mot de passe d'authentification pour l'espace client est obligatoire."

        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO clients (nom, prenom, date_naissance, lieu_naissance, sexe, email, telephone, adresse) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (nom, prenom, str(date_naissance), lieu_naissance, sexe, email, telephone, adresse))
        client_id = cursor.lastrowid

        try:
            cursor.execute("""
                INSERT INTO utilisateurs (username, password, role, email, date_naissance, lieu_naissance, sexe, adresse, client_id) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (username, password_connexion, "client", email, str(date_naissance), lieu_naissance, sexe, adresse,
                  client_id))
            conn.commit()
            success = True
            msg = f"Client enregistré avec succès ! Identifiant de connexion : **{username}**"
        except sqlite3.IntegrityError:
            success = False
            msg = "Ce nom d'utilisateur (username) existe déjà."

        conn.close()
        return success, msg

    def lister(self):
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients")
        result = cursor.fetchall()
        conn.close()
        return result

    def modifier(self, client_id, nom, prenom, date_naissance, lieu_naissance, sexe, email, telephone, adresse):
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE clients SET nom = ?, prenom = ?, date_naissance = ?, lieu_naissance = ?, sexe = ?, email = ?, telephone = ?, adresse = ? 
            WHERE id = ?
        """, (nom, prenom, str(date_naissance), lieu_naissance, sexe, email, telephone, adresse, client_id))
        conn.commit()
        conn.close()

    def supprimer(self, client_id):
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM utilisateurs WHERE client_id = ?", (client_id,))
        cursor.execute("DELETE FROM comptes WHERE client_id = ?", (client_id,))
        cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        conn.commit()
        conn.close()


class CompteBancaire:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def creer(self, numero_compte, type_compte, solde_usd, solde_cdf, code_secret, client_id):
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT date_naissance FROM clients WHERE id = ?", (client_id,))
        res = cursor.fetchone()
        if not res:
            conn.close()
            return False, "Client introuvable."

        date_naiss_str = res[0]
        date_naiss = datetime.strptime(date_naiss_str, "%Y-%m-%d").date()
        today = date.today()
        age = today.year - date_naiss.year - ((today.month, today.day) < (date_naiss.month, date_naiss.day))

        if age < 18:
            conn.close()
            return False, f"Création refusée : Le propriétaire est mineur ({age} ans)."

        try:
            cursor.execute(
                "INSERT INTO comptes (numero_compte, type_compte, solde_usd, solde_cdf, code_secret, client_id) VALUES (?, ?, ?, ?, ?, ?)",
                (numero_compte, type_compte, solde_usd, solde_cdf, code_secret, client_id))
            conn.commit()
            success = True
            msg = "Compte créé avec succès !"
        except sqlite3.IntegrityError:
            success = False
            msg = "Ce numéro de compte existe déjà."
        conn.close()
        return success, msg

    def lister_details(self):
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT comptes.id, comptes.numero_compte, comptes.type_compte, comptes.solde_usd, comptes.solde_cdf, clients.nom, clients.prenom, comptes.client_id 
            FROM comptes JOIN clients ON comptes.client_id = clients.id
        """)
        result = cursor.fetchall()
        conn.close()
        return result

    def modifier(self, compte_id, type_compte, solde_usd, solde_cdf):
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE comptes SET type_compte = ?, solde_usd = ?, solde_cdf = ? WHERE id = ?",
                       (type_compte, solde_usd, solde_cdf, compte_id))
        conn.commit()
        conn.close()

    def supprimer(self, compte_id):
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM comptes WHERE id = ?", (compte_id,))
        conn.commit()
        conn.close()


class OperationBancaire:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def enregistrer_menace(self, username, numero_compte, type_menace, description):
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        date_op = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO journal_securite (username, numero_compte, type_menace, description, date) 
            VALUES (?, ?, ?, ?, ?)
        """, (username, numero_compte, type_menace, description, date_op))
        conn.commit()
        conn.close()

    def verifier_code(self, numero_compte, code_saisi, username):
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT code_secret FROM comptes WHERE numero_compte = ?", (numero_compte,))
        res = cursor.fetchone()
        conn.close()
        if res and res[0] == code_saisi:
            return True
        # Enregistrement automatique de la tentative malveillante (Code secret erroné)
        self.enregistrer_menace(username, numero_compte, "Code secret incorrect",
                                f"Tentative d'accès avec un faux code secret sur le compte {numero_compte}")
        return False

    def effectuer_depot(self, numero_compte, montant, devise):
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        if devise == "USD":
            cursor.execute("SELECT solde_usd FROM comptes WHERE numero_compte = ?", (numero_compte,))
            solde_actuel = cursor.fetchone()[0]
            nouveau_solde = solde_actuel + montant
            cursor.execute("UPDATE comptes SET solde_usd = ? WHERE numero_compte = ?", (nouveau_solde, numero_compte))
        else:
            cursor.execute("SELECT solde_cdf FROM comptes WHERE numero_compte = ?", (numero_compte,))
            solde_actuel = cursor.fetchone()[0]
            nouveau_solde = solde_actuel + montant
            cursor.execute("UPDATE comptes SET solde_cdf = ? WHERE numero_compte = ?", (nouveau_solde, numero_compte))

        date_op = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO operations (numero_compte, type_operation, montant, devise, date) VALUES (?, ?, ?, ?, ?)",
            (numero_compte, "Dépôt", montant, devise, date_op))
        conn.commit()
        conn.close()
        return nouveau_solde

    def effectuer_retrait(self, numero_compte, montant, devise, code_secret, username):
        if not self.verifier_code(numero_compte, code_secret, username):
            return False, "Code secret du compte incorrect !"

        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        if devise == "USD":
            cursor.execute("SELECT solde_usd FROM comptes WHERE numero_compte = ?", (numero_compte,))
            solde_actuel = cursor.fetchone()[0]
            if solde_actuel < montant:
                conn.close()
                self.enregistrer_menace(username, numero_compte, "Tentative de retrait excessif",
                                        f"A tenté de retirer {montant:,.2f} USD alors que le solde est de {solde_actuel:,.2f} USD")
                return False, f"Solde USD insuffisant (Solde actuel : {solde_actuel:,.2f} $)."
            nouveau_solde = solde_actuel - montant
            cursor.execute("UPDATE comptes SET solde_usd = ? WHERE numero_compte = ?", (nouveau_solde, numero_compte))
        else:
            cursor.execute("SELECT solde_cdf FROM comptes WHERE numero_compte = ?", (numero_compte,))
            solde_actuel = cursor.fetchone()[0]
            if solde_actuel < montant:
                conn.close()
                self.enregistrer_menace(username, numero_compte, "Tentative de retrait excessif",
                                        f"A tenté de retirer {montant:,.2f} FC alors que le solde est de {solde_actuel:,.2f} FC")
                return False, f"Solde CDF insuffisant (Solde actuel : {solde_actuel:,.2f} FC)."
            nouveau_solde = solde_actuel - montant
            cursor.execute("UPDATE comptes SET solde_cdf = ? WHERE numero_compte = ?", (nouveau_solde, numero_compte))

        date_op = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO operations (numero_compte, type_operation, montant, devise, date) VALUES (?, ?, ?, ?, ?)",
            (numero_compte, "Retrait", montant, devise, date_op))
        conn.commit()
        conn.close()
        return True, nouveau_solde

    def effectuer_virement(self, compte_source, compte_dest, montant, devise, code_secret, username):
        if not self.verifier_code(compte_source, code_secret, username):
            return False, "Code secret du compte source incorrect !"

        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        if devise == "USD":
            cursor.execute("SELECT solde_usd FROM comptes WHERE numero_compte = ?", (compte_source,))
            solde_src = cursor.fetchone()[0]
            if solde_src < montant:
                conn.close()
                self.enregistrer_menace(username, compte_source, "Tentative de virement excessif",
                                        f"A tenté de virer {montant:,.2f} USD avec un solde de {solde_src:,.2f} USD")
                return False, "Solde USD insuffisant pour ce virement."
            cursor.execute("SELECT solde_usd FROM comptes WHERE numero_compte = ?", (compte_dest,))
            solde_dst = cursor.fetchone()[0]

            cursor.execute("UPDATE comptes SET solde_usd = ? WHERE numero_compte = ?",
                           (solde_src - montant, compte_source))
            cursor.execute("UPDATE comptes SET solde_usd = ? WHERE numero_compte = ?",
                           (solde_dst + montant, compte_dest))
        else:
            cursor.execute("SELECT solde_cdf FROM comptes WHERE numero_compte = ?", (compte_source,))
            solde_src = cursor.fetchone()[0]
            if solde_src < montant:
                conn.close()
                self.enregistrer_menace(username, compte_source, "Tentative de virement excessif",
                                        f"A tenté de virer {montant:,.2f} FC avec un solde de {solde_src:,.2f} FC")
                return False, "Solde CDF insuffisant pour ce virement."
            cursor.execute("SELECT solde_cdf FROM comptes WHERE numero_compte = ?", (compte_dest,))
            solde_dst = cursor.fetchone()[0]

            cursor.execute("UPDATE comptes SET solde_cdf = ? WHERE numero_compte = ?",
                           (solde_src - montant, compte_source))
            cursor.execute("UPDATE comptes SET solde_cdf = ? WHERE numero_compte = ?",
                           (solde_dst + montant, compte_dest))

        date_op = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO operations (numero_compte, type_operation, montant, devise, date) VALUES (?, ?, ?, ?, ?)",
            (compte_source, "Virement (Débit)", montant, devise, date_op))
        cursor.execute(
            "INSERT INTO operations (numero_compte, type_operation, montant, devise, date) VALUES (?, ?, ?, ?, ?)",
            (compte_dest, "Virement (Crédit)", montant, devise, date_op))
        conn.commit()
        conn.close()
        return True, "Virement effectué avec succès !"

    def historique(self, numero_compte=None):
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        if numero_compte:
            cursor.execute("SELECT * FROM operations WHERE numero_compte = ? ORDER BY date DESC", (numero_compte,))
        else:
            cursor.execute("SELECT * FROM operations ORDER BY date DESC")
        result = cursor.fetchall()
        conn.close()
        return result

db = DatabaseManager()
user_manager = UserManager(db)
security_scanner = SecurityScanner(db)
client_manager = Client(db)
compte_manager = CompteBancaire(db)
op_manager = OperationBancaire(db)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.client_id = None

if not st.session_state.logged_in:
    st.sidebar.title("🔐 Connexion au Système")
    username = st.sidebar.text_input("Nom d'utilisateur", value="agent")
    password = st.sidebar.text_input("Mot de passe", type="password", value="agent123")

    if st.sidebar.button("Se connecter"):
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role, client_id FROM utilisateurs WHERE username = ? AND password = ?",
                       (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = user[0]
            st.session_state.client_id = user[1]
            st.rerun()
        else:
            st.sidebar.error("Nom d'utilisateur ou mot de passe incorrect.")

    st.title("🏦 Système de Gestion Bancaire - UPN")
    st.info("Connectez-vous via le panneau latéral.")
    st.stop()

st.sidebar.write(f"Connecté : **{st.session_state.username}**")
st.sidebar.write(f"Rôle : **{st.session_state.role.upper()}**")
if st.sidebar.button("Déconnexion"):
    st.session_state.logged_in = False
    st.session_state.pop("menu_selection", None)
    st.rerun()

role = st.session_state.role
menu_options = []

if role == "admin":
    menu_options = ["Accueil", "Gestion des clients", "Gestion des comptes", "Opérations", "Historique Global",
                    "⚙️ Administration"]
elif role == "agent":
    menu_options = ["Accueil", "Gestion des clients", "Gestion des comptes", "Opérations", "Historique Global"]
elif role == "client":
    menu_options = ["Mes Comptes & Solde", "Effectuer un virement", "Mon Historique"]

if "menu_selection" not in st.session_state or st.session_state.menu_selection not in menu_options:
    st.session_state.menu_selection = menu_options[0]

menu = st.sidebar.radio("Navigation", menu_options, index=menu_options.index(st.session_state.menu_selection),
                        key="menu_radio")
st.session_state.menu_selection = menu

if menu == "Accueil":
    st.title("📊 Tableau de Bord")
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM clients")
    nb_clients = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM comptes")
    nb_comptes = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(solde_usd), SUM(solde_cdf) FROM comptes")
    res_solde = cursor.fetchone()
    total_usd = res_solde[0] or 0.0
    total_cdf = res_solde[1] or 0.0
    conn.close()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Clients enregistrés", nb_clients)
    col2.metric("Comptes actifs", nb_comptes)
    col3.metric("Masse USD", f"{total_usd:,.2f} $")
    col4.metric("Masse CDF", f"{total_cdf:,.2f} FC")

elif menu == "Gestion des clients":
    st.title("👤 Gestion des Clients")

    with st.form("form_client"):
        st.subheader("Enregistrer un nouveau client (18 ans min)")
        nom = st.text_input("Nom")
        prenom = st.text_input("Prénom")
        date_naissance = st.date_input("Date de naissance", value=date(2000, 1, 1), min_value=date(1900, 1, 1),
                                       max_value=date.today())
        lieu_naissance = st.text_input("Lieu de naissance")
        sexe = st.selectbox("Sexe", ["Masculin", "Féminin", "Autre"])
        email = st.text_input("Adresse Email")
        telephone = st.text_input("Téléphone")
        adresse = st.text_input("Adresse physique")

        st.markdown("---")
        st.subheader("Paramètres de Connexion Espace Client")
        username_connexion = st.text_input("Nom d'utilisateur (Username)")
        password_connexion = st.text_input("Mot de passe de connexion", type="password")

        submit = st.form_submit_button("Enregistrer")

        if submit and nom and prenom:
            succes, message = client_manager.ajouter(
                nom, prenom, date_naissance, lieu_naissance, sexe,
                email, telephone, adresse, username_connexion, password_connexion
            )
            if succes:
                st.success(message)
            else:
                st.error(message)

    st.subheader("Liste des clients")
    clients = client_manager.lister()
    if clients:
        st.table(clients)
    else:
        st.info("Aucun client enregistré.")

elif menu == "Gestion des comptes":
    st.title("📁 Gestion des Comptes Bancaires (Double Monnaie)")

    clients_list = client_manager.lister()
    client_dict = {f"{c[1]} {c[2]} (Né(e) le {c[3]})": c[0] for c in clients_list}

    with st.form("form_compte"):
        st.subheader("Créer un compte avec soldes USD et CDF")
        selected_client_str = st.selectbox("Sélectionner le client",
                                           list(client_dict.keys()) if client_dict else ["Aucun client"])
        type_compte = st.selectbox("Type de compte", ["Courant", "Épargne", "Professionnel"])
        numero_compte = st.text_input("Numéro de compte unique (ex: ACC-001)")

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            solde_initial_usd = st.number_input("Solde initial USD ($)", min_value=0.0, value=0.0)
        with col_s2:
            solde_initial_cdf = st.number_input("Solde initial CDF (FC)", min_value=0.0, value=0.0)

        code_secret = st.text_input("Code secret du compte", type="password")

        submit_compte = st.form_submit_button("Créer le compte")

        if submit_compte and client_dict and numero_compte and code_secret:
            client_id = client_dict[selected_client_str]
            succes, message = compte_manager.creer(numero_compte, type_compte, solde_initial_usd, solde_initial_cdf,
                                                   code_secret, client_id)
            if succes:
                st.success(message)
            else:
                st.error(message)

    st.subheader("Liste des comptes")
    comptes = compte_manager.lister_details()
    if comptes:
        data_to_show = [[c[1], c[2], f"{c[3]:,.2f} $", f"{c[4]:,.2f} FC", c[5], c[6]] for c in comptes]
        st.table(data_to_show)
    else:
        st.info("Aucun compte trouvé.")

elif menu == "Opérations":
    st.title("💸 Opérations Bancaires & Historique")

    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT numero_compte FROM comptes")
    comptes_list = [c[0] for c in cursor.fetchall()]
    conn.close()

    if not comptes_list:
        st.warning("Veuillez d'abord créer un compte bancaire.")
    else:
        op_type = st.selectbox("Type d'opération", ["Dépôt", "Retrait", "Virement"])
        devise = st.selectbox("Devise", ["USD", "FC"])
        compte_source = st.selectbox("Numéro de compte", comptes_list)
        montant = st.number_input("Montant", min_value=0.0, value=0.0)

        code_secret = ""
        if op_type in ["Retrait", "Virement"]:
            code_secret = st.text_input("Entrez le code secret du compte", type="password")

        if op_type == "Virement":
            compte_dest = st.selectbox("Compte destinataire", [c for c in comptes_list if c != compte_source])

        if st.button("Valider l'opération"):
            if op_type == "Dépôt":
                nouveau_solde = op_manager.effectuer_depot(compte_source, montant, devise)
                st.success(f"Dépôt réussi. Nouveau solde : {nouveau_solde:,.2f} {devise}")

            elif op_type == "Retrait":
                succes, message = op_manager.effectuer_retrait(compte_source, montant, devise, code_secret,
                                                               st.session_state.username)
                if succes:
                    st.success(f"Retrait réussi. Nouveau solde : {message:,.2f} {devise}")
                else:
                    st.error(message)

            elif op_type == "Virement" and 'compte_dest' in locals():
                succes, message = op_manager.effectuer_virement(compte_source, compte_dest, montant, devise,
                                                                code_secret, st.session_state.username)
                if succes:
                    st.success(message)
                else:
                    st.error(message)

elif menu == "Historique Global":
    st.title("📈 Historique des Transactions")
    ops = op_manager.historique()
    if ops:
        st.table(ops)
    else:
        st.info("Aucune opération enregistrée.")

elif menu == "Mes Comptes & Solde":
    st.title("💳 Mes Comptes Bancaires (USD & CDF)")
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT numero_compte, type_compte, solde_usd, solde_cdf FROM comptes WHERE client_id = ?",
                   (st.session_state.client_id,))
    mes_comptes = cursor.fetchall()
    conn.close()

    if mes_comptes:
        for c in mes_comptes:
            st.info(
                f"**Numéro :** {c[0]} | **Type :** {c[1]} | **Solde USD :** {c[2]:,.2f} $ | **Solde CDF :** {c[3]:,.2f} FC")
    else:
        st.warning("Aucun compte associé à votre profil.")

elif menu == "Effectuer un virement":
    st.title("💸 Opérations sur mon compte")

    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT numero_compte FROM comptes WHERE client_id = ?", (st.session_state.client_id,))
    mes_comptes = [c[0] for c in cursor.fetchall()]

    cursor.execute("SELECT numero_compte FROM comptes")
    tous_comptes = [c[0] for c in cursor.fetchall()]
    conn.close()

    if not mes_comptes:
        st.warning("Vous ne possédez aucun compte pour effectuer des opérations.")
    else:
        type_op_client = st.selectbox("Type d'opération", ["Dépôt", "Retrait", "Virement"])
        devise = st.selectbox("Devise", ["USD", "FC"])
        compte_src = st.selectbox("Mon compte", mes_comptes)
        montant = st.number_input("Montant", min_value=0.0, value=0.0)

        code_secret = ""
        if type_op_client in ["Retrait", "Virement"]:
            code_secret = st.text_input("Code secret de mon compte", type="password")

        compte_dest = None
        if type_op_client == "Virement":
            compte_dest = st.selectbox("Compte destinataire", [c for c in tous_comptes if c != compte_src])

        if st.button("Valider l'opération"):
            if type_op_client == "Dépôt":
                nouveau_solde = op_manager.effectuer_depot(compte_src, montant, devise)
                st.success(f"Dépôt réussi. Nouveau solde : {nouveau_solde:,.2f} {devise}")

            elif type_op_client == "Retrait":
                succes, message = op_manager.effectuer_retrait(compte_src, montant, devise, code_secret,
                                                               st.session_state.username)
                if succes:
                    st.success(f"Retrait réussi. Nouveau solde : {message:,.2f} {devise}")
                else:
                    st.error(message)

            elif type_op_client == "Virement" and compte_dest:
                succes, message = op_manager.effectuer_virement(compte_src, compte_dest, montant, devise, code_secret,
                                                                st.session_state.username)
                if succes:
                    st.success(message)
                else:
                    st.error(message)

elif menu == "Mon Historique":
    st.title("📋 Historique de mes transactions")
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT numero_compte FROM comptes WHERE client_id = ?", (st.session_state.client_id,))
    mes_comptes = [c[0] for c in cursor.fetchall()]
    conn.close()

    if mes_comptes:
        compte_choisi = st.selectbox("Choisir un compte", mes_comptes)
        ops = op_manager.historique(compte_choisi)
        if ops:
            st.table(ops)
        else:
            st.info("Aucune transaction pour ce compte.")
    else:
        st.warning("Aucun compte disponible.")

elif menu == "⚙️ Administration" and role == "admin":
    st.title("⚙️ Panneau d'Administration")
    tab1, tab2, tab3, tab4 = st.tabs(
        ["Gestion Clients", "Gestion Comptes", "Gestion Agents", "🚨 Détection Malveillants"])

    with tab1:
        clients = client_manager.lister()
        if clients:
            client_dict_admin = {f"{c[1]} {c[2]} (ID: {c[0]})": c[0] for c in clients}
            selected_c = st.selectbox("Choisir un client", list(client_dict_admin.keys()))
            c_id = client_dict_admin[selected_c]
            current = [c for c in clients if c[0] == c_id][0]

            with st.form("form_upd_client"):
                n_nom = st.text_input("Nom", value=current[1])
                n_prenom = st.text_input("Prénom", value=current[2])
                n_date = st.date_input("Date de naissance", value=datetime.strptime(current[3], "%Y-%m-%d").date())
                n_lieu = st.text_input("Lieu de naissance", value=current[4] if current[4] else "")
                n_sexe = st.selectbox("Sexe", ["Masculin", "Féminin", "Autre"],
                                      index=["Masculin", "Féminin", "Autre"].index(current[5]) if current[5] in [
                                          "Masculin", "Féminin", "Autre"] else 0)
                n_email = st.text_input("Adresse Email", value=current[6] if current[6] else "")
                n_tel = st.text_input("Téléphone", value=current[7] if current[7] else "")
                n_adr = st.text_input("Adresse", value=current[8] if current[8] else "")

                c1, c2 = st.columns(2)
                with c1:
                    if st.form_submit_button("Modifier"):
                        client_manager.modifier(c_id, n_nom, n_prenom, n_date, n_lieu, n_sexe, n_email, n_tel, n_adr)
                        st.success("Modifié avec succès !")
                        st.rerun()
                with c2:
                    if st.form_submit_button("Supprimer"):
                        client_manager.supprimer(c_id)
                        st.warning("Client supprimé !")
                        st.rerun()
        else:
            st.info("Aucun client.")

    with tab2:
        comptes = compte_manager.lister_details()
        if comptes:
            compte_dict_admin = {f"Compte n° {c[1]} ({c[5]} {c[6]})": c[0] for c in comptes}
            selected_cp = st.selectbox("Choisir un compte", list(compte_dict_admin.keys()))
            cp_id = compte_dict_admin[selected_cp]
            current_cp = [c for c in comptes if c[0] == cp_id][0]

            with st.form("form_upd_compte"):
                n_type = st.selectbox("Type", ["Courant", "Épargne", "Professionnel"],
                                      index=["Courant", "Épargne", "Professionnel"].index(current_cp[2]))
                n_solde_usd = st.number_input("Solde USD ($)", value=float(current_cp[3]))
                n_solde_cdf = st.number_input("Solde CDF (FC)", value=float(current_cp[4]))

                c1, c2 = st.columns(2)
                with c1:
                    if st.form_submit_button("Modifier Compte"):
                        compte_manager.modifier(cp_id, n_type, n_solde_usd, n_solde_cdf)
                        st.success("Compte mis à jour !")
                        st.rerun()
                with c2:
                    if st.form_submit_button("Supprimer Compte"):
                        compte_manager.supprimer(cp_id)
                        st.warning("Compte supprimé !")
                        st.rerun()
        else:
            st.info("Aucun compte.")

    with tab3:
        st.subheader("Créer un nouvel agent")
        with st.form("form_creer_agent"):
            new_agent_user = st.text_input("Nom d'utilisateur de l'agent")
            new_agent_pass = st.text_input("Mot de passe de l'agent", type="password", value="agent123")
            new_agent_email = st.text_input("Adresse Email")
            new_agent_lieu = st.text_input("Lieu de naissance")
            new_agent_sexe = st.selectbox("Sexe", ["Masculin", "Féminin", "Autre"], key="agent_sexe")
            new_agent_adresse = st.text_input("Adresse physique")
            new_agent_fonction = st.selectbox("Fonction",
                                              ["Gestionnaire de comptes", "Caissier", "Chargé de crédit", "Superviseur",
                                               "Agent d'accueil"])

            submit_agent = st.form_submit_button("Créer l'agent")

            if submit_agent and new_agent_user:
                succes, msg = user_manager.creer_agent(
                    username=new_agent_user,
                    password=new_agent_pass,
                    email=new_agent_email,
                    lieu_naissance=new_agent_lieu,
                    sexe=new_agent_sexe,
                    adresse=new_agent_adresse,
                    fonction=new_agent_fonction
                )
                if succes:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        st.subheader("Liste et suppression des agents")
        agents_list = user_manager.lister_agents()
        if agents_list:
            agent_dict = {f"{a[1]} - {a[7]} (Email: {a[2]})": a[0] for a in agents_list}
            selected_agent_str = st.selectbox("Sélectionner un agent", list(agent_dict.keys()))

            if st.button("Supprimer cet agent"):
                agent_id_to_del = agent_dict[selected_agent_str]
                user_manager.supprimer_agent(agent_id_to_del)
                st.warning("Agent supprimé avec succès !")
                st.rerun()
        else:
            st.info("Aucun autre agent enregistré.")

    with tab4:
        st.subheader("🔍 Journal des comportements malveillants & Fraudes tentées")

        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, numero_compte, type_menace, description, date FROM journal_securite ORDER BY date DESC")
        menaces = cursor.fetchall()
        conn.close()

        if menaces:
            st.warning(f"⚠️ {len(menaces)} tentative(s) suspecte(s) enregistrée(s) dans le système !")
            for m in menaces:
                st.error(
                    f"**Date :** {m[5]} | **Utilisateur (Auteur) :** `{m[1]}` | **Compte visé :** `{m[2]}`\n\n**Type de menace :** {m[3]}\n\n*Détails :* {m[4]}")
        else:
            st.success("✅ Aucune tentative malveillante enregistrée pour le moment.")
