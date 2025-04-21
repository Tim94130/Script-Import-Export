# Importation des bibliothèques nécessaires
import pandas as pd
from tkinter import Tk, filedialog
import os
import re
import json
import requests
from time import sleep
import unicodedata
from collections import defaultdict
from rapidfuzz import process, fuzz  # Si nécessaireimport csv
import csv
import MySQLdb


# Définitions globales pour la détection des couleurs
adjectifs_ignores = [
    "dark",
    "light",
    "pale",
    "deep",
    "bright",
    "medium",
    "fonce",
    "foncé",
    "clair",
    "pâle",
    "flashy",
    "fluorescent",
]

couleurs_base = [
    "white",
    "black",
    "brown",
    "blue",
    "red",
    "pink",
    "green",
    "grey",
    "gray",
    "yellow",
    "orange",
    "purple",
    "violet",
    "beige",
    "gold",
    "silver",
    "taupe",
    "cyan",
    "magenta",
    "navy",
    "maroon",
    "lime",
    "olive",
    "teal",
    "aqua",
    "blanc",
    "noir",
    "marron",
    "brun",
    "bleu",
    "rouge",
    "rose",
    "vert",
    "gris",
    "jaune",
    "violet",
    "beige",
    "doré",
    "argent",
    "kaki",
    "turquoise",
    "fuchsia",
    "lavande",
    "ocre",
    "ivory",
    "ivoires",
    "argenté",
    "rose gold",
    "off white",
    "peach pink",
    "sepia black",
    "golden",
    "sable",
    "chocolat",
    "prune",
    "dark brown",
]

mapping_couleurs = {
    "white": "Blanc",
    "off white": "Blanc cassé",
    "ivory": "Blanc cassé",
    "blanc": "Blanc",
    "dark brown": "Marron",
    "black": "Noir",
    "noir": "Noir",
    "sepia black": "Noir",
    "brown": "Marron",
    "brun": "Marron",
    "marron": "Marron",
    "chocolat": "Marron",
    "red": "Rouge",
    "rouge": "Rouge",
    "pink": "Rose",
    "rose": "Rose",
    "peach pink": "Rose",
    "green": "Vert",
    "vert": "Vert",
    "leaf green": "Vert",
    "grey": "Gris",
    "gray": "Gris",
    "gris": "Gris",
    "mirage grey": "Gris",
    "yellow": "Jaune",
    "jaune": "Jaune",
    "orange": "Orange",
    "purple": "Violet",
    "violet": "Violet",
    "lavande": "Violet",
    "prune": "Violet",
    "beige": "Beige",
    "sable": "Beige",
    "taupe": "Taupe",
    "gold": "Doré",
    "golden": "Doré",
    "rose gold": "Rose Gold",
    "silver": "Argent",
    "argent": "Argent",
    "argenté": "Argent",
    "kaki": "Kaki",
    "fuchsia": "Fuchsia",
    "magenta": "Fuchsia",
    "blue": "Bleu",
    "bleu": "Bleu",
    "navy": "Bleu marine",
    "cyan": "Cyan",
    "aqua": "Cyan",
    "turquoise": "Turquoise",
    "maroon": "Bordeaux",
    "bordeaux": "Bordeaux",
    "lime": "Vert clair",
    "olive": "Vert olive",
    "teal": "Bleu-vert",
}


############################################
# Fonctions de transformation du CSV
############################################


def renommer_colonnes_pour_woocommerce(df):
    correspondance_woocommerce = {
        "Référence": "SKU",
        "Nom de l'article (en Français)": "Name",
        "Description courte (en Français)": "Short description",
        "Description (en Français)": "Description",
        "Prix pour le groupe Défaut": "Regular price",
        "Stock - Quantité": "Stock",
        "Option Couleur (en Français)": "Attribute 1 value(s)",
        "Option Taille (en Français)": "Attribute 2 value(s)",
        "Poids (en Kg)": "Weight (kg)",
        "Longueur (en cm)": "Length (cm)",
        "Largeur (en cm)": "Width (cm)",
        "Hauteur (en cm)": "Height (cm)",
        "Catégories": "Categories",
        "Parent": "Parent",
        "Images": "Images",
        "Garantie": "Warranty",
        "Pays de fabrication": "Country of manufacture",
        "Marque": "Brands",
    }
    df.rename(columns=correspondance_woocommerce, inplace=True)
    return df


def supprimer_doublons_colonnes(df):
    correspondance_woocommerce = {
        "Référence": "SKU",
        "Nom de l'article (en Français)": "Name",
        "Description courte (en Français)": "Short description",
        "Description (en Français)": "Description",
        "Prix pour le groupe Défaut": "Regular price",
        "Prix de vente conseillé": "Sale price",
        "Stock - Quantité": "Stock",
        "Option Couleur (en Français)": "Attribute 1 value(s)",
        "Option Taille (en Français)": "Attribute 2 value(s)",
        "Poids (en Kg)": "Weight (kg)",
        "Longueur (en cm)": "Length (cm)",
        "Largeur (en cm)": "Width (cm)",
        "Hauteur (en cm)": "Height (cm)",
        "Catégories": "Categories",
        "Parent": "Parent",
        "Images": "Images",
        "Garantie": "Warranty",
        "Pays de fabrication": "Country of manufacture",
        "Marque": "Brands",
    }
    colonnes_presentes = df.columns
    colonnes_a_supprimer = [
        fr_col
        for fr_col, en_col in correspondance_woocommerce.items()
        if fr_col in colonnes_presentes and en_col in colonnes_presentes
    ]
    df.drop(columns=colonnes_a_supprimer, inplace=True, errors="ignore")
    return df


def ajuster_categories(df):
    colonnes_categories = [
        "Nom de la catégorie de niveau 1 (en Français)",
        "Nom de la catégorie de niveau 2 (en Français)",
        "Nom de la catégorie de niveau 3 (en Français)",
        "Nom de la catégorie de niveau 4 (en Français)",
    ]
    colonnes_existantes = [col for col in colonnes_categories if col in df.columns]
    if colonnes_existantes:
        df["Categories"] = df[colonnes_existantes].apply(
            lambda x: " > ".join(x.dropna()), axis=1
        )
    if "Catégorie principale du produit" in df.columns:
        df["Categories"] = df.apply(
            lambda x: f"{x['Categories']} | {x['Catégorie principale du produit']}"
            if pd.notnull(x["Catégorie principale du produit"])
            else x["Categories"],
            axis=1,
        )
    df.drop(
        columns=colonnes_existantes + ["Catégorie principale du produit"],
        inplace=True,
        errors="ignore",
    )
    return df


def formatter_images(df, taille_lot=100):
    base_url = "https://dev.yolobaby.online/wp-content/uploads/image-site/"

    colonnes_images = [
        "Image principale",
        "Image supplémentaire n°1",
        "Image supplémentaire n°2",
        "Image supplémentaire n°3",
        "Image supplémentaire n°4",
        "Image supplémentaire n°5",
        "Image supplémentaire n°6",
        "Image supplémentaire n°7",
        "Image supplémentaire n°8",
        "Image supplémentaire n°9",
    ]

    colonnes_existantes = [col for col in colonnes_images if col in df.columns]

    if not colonnes_existantes:
        print("⚠️ Aucune colonne d'image trouvée.")
        return df

    # Fusion des URLs complètes dans une nouvelle colonne temporaire
    df["all_image_urls"] = df[colonnes_existantes].apply(
        lambda row: [base_url + img.strip() for img in row.dropna().astype(str)], axis=1
    )

    # Génération directe de la colonne "Images"
    df["Images"] = df["all_image_urls"].apply(lambda urls: ", ".join(urls))

    # --- 👇 Partie désactivée : récupération des IDs depuis l’API + images supplémentaires ---

    # Créer une liste unique de toutes les URLs pour minimiser les appels API
    # toutes_urls = list(set(url for sublist in df["all_image_urls"] for url in sublist))

    # Récupérer les IDs en batch depuis l'API
    # url_to_id = recuperer_id_images_wp_via_api_batch(toutes_urls, taille_lot)

    # Associer les IDs récupérés aux URLs dans le DataFrame
    # def generer_meta(row):
    #     urls_sup = row["all_image_urls"][1:]  # images supplémentaires uniquement
    #     ids_sup = [str(url_to_id[url]) for url in urls_sup if url in url_to_id]
    #     return ",".join(ids_sup)

    # df["_wc_additional_variation_images"] = df.apply(generer_meta, axis=1)

    # --- ☝️ Fin de la partie désactivée ---

    # Nettoyage
    df.drop(
        columns=colonnes_existantes + ["all_image_urls"], inplace=True, errors="ignore"
    )

    return df


# --- 👇 Fonction API désactivée mais conservée si besoin futur ---
# def recuperer_id_images_wp_via_api_batch(urls, taille_lot=100):
#     api_url = "https://dev.yolobaby.online/api-images.php"
#     url_to_id = {}

#     for i in range(0, len(urls), taille_lot):
#         lot_urls = urls[i : i + taille_lot]
#         try:
#             response = requests.post(
#                 api_url, json={"urls": lot_urls, "api_key": "12345"}
#             )
#             response.raise_for_status()
#             resultat = response.json()
#             url_to_id.update(resultat)
#             print(
#                 f"✅ Lot {i // taille_lot + 1}/{(len(urls) - 1) // taille_lot + 1} traité avec succès."
#             )
#         except requests.RequestException as e:
#             print(f"❌ Erreur API sur le lot {i // taille_lot + 1}: {e}")
#             print(f"Réponse reçue : {response.text}")
#             sleep(1)  # Pause en cas d'erreur pour éviter surcharge API

#     return url_to_id

#
############################################
# Fonctions de détection/extraction des couleurs
############################################


def detecter_toutes_couleurs(nom_produit: str):
    if not isinstance(nom_produit, str):
        return []

    original = nom_produit
    texte = nom_produit.lower().strip()

    # 1. Tentative stricte avec mapping
    tokens = re.split(r"[\s\-\|\(\),/]+", texte)
    trouvees = [mapping_couleurs[t] for t in tokens if t in mapping_couleurs]
    if trouvees:
        print(f"[🎯 Mapping] '{original}' -> {trouvees}")
        return list(dict.fromkeys(trouvees))

    # 2. Fallback intelligent
    texte = texte.split("|")[0].strip()  # On coupe avant la marque
    mots = texte.split()

    candidates = []
    for i in range(len(mots)):
        if i + 1 < len(mots):
            candidat = f"{mots[i]} {mots[i+1]}"
            if candidat not in mapping_couleurs and candidat not in texte:
                candidates.append(candidat)
        candidates.append(mots[i])

    # Filtrage simple des mots communs inutiles
    mots_inutiles = {"bébé", "bébés", "junior", "lunettes", "enfants", "d", "c", "mini", "soleil", "0-9", "3-5", "9-36", "mois", "ans", "ans)", "ans."}
    filtered = [mot for mot in candidates if mot not in mots_inutiles and len(mot) > 2]

    if filtered:
        print(f"[🌀 Fallback] '{original}' -> {filtered[0].title()}")
        return [filtered[0].title()]  # On retourne le premier qui semble pertinent

    return []



# Renvoie un dictionnaire contenant les couleurs détectées
def determiner_si_variable(
    nom_produit: str, option_taille: str = "", couleurs_detectees: list = None
):
    """
    Un produit est considéré comme variable s’il :
    - contient exactement UNE couleur détectée (mapping ou heuristique),
    - ou contient une taille détectée via pattern intelligent.
    """
    if couleurs_detectees is None:
        couleurs_detectees = detecter_toutes_couleurs(nom_produit)

    # Sécurisation pour la taille
    taille = str(option_taille).strip().lower() if pd.notnull(option_taille) else ""
    contient_taille = (
        bool(re.search(r"(mois|ans|kg|g|taille|age|m|t)", taille))
        and len(taille) <= 15
    )

    # S’il y a une couleur (même détectée librement) ou une taille
    return len(couleurs_detectees) >= 1 or contient_taille


def detecter_taille_dans_nom(nom_produit: str):
    if not isinstance(nom_produit, str):
        return ""

    texte = (
        unicodedata.normalize("NFKD", nom_produit)
        .encode("ascii", "ignore")
        .decode("utf-8")
        .lower()
    )

    patterns = [
        r"\b\d{1,2}\s?[-àa]\s?\d{1,2}\s?(mois|ans|kg|m|a)\b",  # 9-36 mois, 3 à 6 kg
        r"\b(?:taille\s?)?(\d{1,2}[+]?)(\s?\([^)]+\))?",  # Taille 2, Taille 4+
        r"\b(?:taille\s?)?(premier|1er|2eme|2e|3eme|3e)\s?age\b",  # 1er âge
        r"\b(\d{2,4})\s?(g|grammes)\b",  # 400g, 800 grammes
        r"\b(croissance|junior|enfant|bebe|bébé|nourrisson)\b",  # mots clés génériques
    ]

    for pattern in patterns:
        match = re.search(pattern, texte)
        if match:
            return match.group(0).strip()

    return ""



def nettoyer_nom_pour_parent(nom_produit: str) -> str:
    """
    Nettoie un nom de produit pour créer une version parent sans taille ni couleur.
    """
    if not isinstance(nom_produit, str):
        return nom_produit

    # 1. Retirer les tailles
    nom = re.sub(r"\b\d{1,2}[- ]?(?:36|24|12|9|6|5|4|3|2|1)? ?(?:mois|ans|an|m|g|kg|taille)\b", "", nom_produit, flags=re.IGNORECASE)

    # 2. Retirer les couleurs détectées (via mapping + fallback)
    couleurs = detecter_toutes_couleurs(nom)
    for couleur in couleurs:
        nom = re.sub(rf"\b{re.escape(couleur)}\b", "", nom, flags=re.IGNORECASE)

    # 3. Nettoyage final : enlever les multiples espaces, tirets inutiles, etc.
    nom = re.sub(r"[-|,]+", " ", nom)
    nom = re.sub(r"\s+", " ", nom).strip()

    # Fallback : si le nom est vide ou trop court, on renvoie le nom original brut (nettoyé minimalement)
    if len(nom) < 5:
        nom = re.sub(r"\s+", " ", nom_produit).strip()

    return nom

# 📌 Fonction pour regrouper les produits **variables** par couleur
def regrouper_variations_par_taille_et_couleur(df):
    """
    Regroupe les produits variables par taille et couleur.
    Crée un parent + variations pour chaque groupe cohérent.
    """
    groupes = {}

    # Étape 1 : constitution des groupes
    for _, row in df.iterrows():
        nom_base = nettoyer_nom_pour_parent(str(row["Name"]))
        groupes.setdefault(nom_base.lower(), []).append(row)

    liste_resultats = []

    # Étape 2 : traitement groupe par groupe
    for _, rows in groupes.items():
        tailles_group = set()
        couleurs_group = set()

        for r in rows:
            tailles_group.add(r.get("Taille détectée", "").strip())
            couleur_str = r.get("Couleurs détectées", "").strip()
            couleurs = [c.strip() for c in couleur_str.split(",") if c.strip()]
            couleurs_group.update(couleurs)

        # Création du parent
        parent = rows[0].copy()
        sku_orig = str(parent["SKU"]).strip()
        nom_parent = nettoyer_nom_pour_parent(parent["Name"])

        parent["SKU"] = "PARENT-" + sku_orig
        parent["Name"] = nom_parent
        parent["Type"] = "variable"

        parent["Attribute 1 name"] = "Couleur"
        parent["Attribute 1 value(s)"] = ", ".join(sorted(couleurs_group))
        parent["Attribute 1 visible"] = "yes"
        parent["Attribute 1 global"] = "yes"

        parent["Attribute 2 name"] = "Taille"
        parent["Attribute 2 value(s)"] = ", ".join(sorted(tailles_group))
        parent["Attribute 2 visible"] = "yes"
        parent["Attribute 2 global"] = "yes"

        parent["Parent SKU"] = ""
        parent["EAN"] = ""
        parent["Code EAN"] = ""
        liste_resultats.append(parent)

        # Création des variations
        for row in rows:
            variation = row.copy()
            variation["Type"] = "variation"
            variation["Parent SKU"] = parent["SKU"]

            couleurs = [c.strip() for c in row.get("Couleurs détectées", "").split(",") if c.strip()]
            couleur_val = ", ".join(couleurs)
            taille_val = row.get("Taille détectée", "").strip()

            variation["Attribute 1 name"] = "Couleur"
            variation["Attribute 1 value(s)"] = couleur_val
            variation["Attribute 1 visible"] = "yes"
            variation["Attribute 1 global"] = "yes"

            variation["Attribute 2 name"] = "Taille"
            variation["Attribute 2 value(s)"] = taille_val
            variation["Attribute 2 visible"] = "yes"
            variation["Attribute 2 global"] = "yes"

            suffix_taille = taille_val[:2].upper() if taille_val else "XX"
            suffix_couleur = couleurs[0][:2].upper() if couleurs else "YY"
            variation["SKU"] = f"{sku_orig}-{suffix_taille}{suffix_couleur}"

            # Nettoyage du nom de variation (on garde le nom du parent)
            variation["Name"] = nom_parent

            liste_resultats.append(variation)

    return pd.DataFrame(liste_resultats)



def main():
    root = Tk()
    root.withdraw()

    chemin_fichier = filedialog.askopenfilename(
        filetypes=[("CSV Files", "*.csv")], title="Sélectionnez le fichier CSV"
    )
    if not chemin_fichier:
        print("❌ Aucun fichier sélectionné. Fermeture du script.")
        return

    try:
        # Chargement du CSV
        df = pd.read_csv(chemin_fichier, encoding="utf-8-sig", dtype=str)
        print(f"📂 Fichier chargé : {os.path.basename(chemin_fichier)}")

        df.columns = df.columns.str.strip()
        print("🔍 Colonnes détectées :", df.columns.tolist())

        df = renommer_colonnes_pour_woocommerce(df)
        print("✅ Colonnes après renommage :", df.columns.tolist())

        if "Name" not in df.columns:
            raise KeyError(
                f"❌ La colonne 'Name' est absente après transformation ! Colonnes actuelles : {df.columns.tolist()}"
            )

        for col in ["Attribute 1 value(s)", "Attribute 2 value(s)"]:
            if col not in df.columns:
                df[col] = ""
            else:
                df[col] = df[col].fillna("").astype(str).str.strip()

        # Détection automatique taille & couleur si manquantes
        df["Taille détectée"] = df.apply(
            lambda row: row["Attribute 2 value(s)"]
            if row["Attribute 2 value(s)"]
            else detecter_taille_dans_nom(row["Name"]),
            axis=1,
        )
        df["Couleurs détectées"] = df.apply(
            lambda row: row["Attribute 1 value(s)"]
            if row["Attribute 1 value(s)"]
            else ", ".join(detecter_toutes_couleurs(row["Name"])),
            axis=1,
        )

        df.drop_duplicates(
            subset=["SKU", "Name", "Taille détectée", "Couleurs détectées"],
            inplace=True,
        )

        df = supprimer_doublons_colonnes(df)
        df = ajuster_categories(df)
        df = formatter_images(df, taille_lot=50)

        df["Type"] = "variable"
        print(f"🛠️ Produits variables détectés : {len(df)}")

        df["Is_Variable"] = df.apply(
            lambda row: determiner_si_variable(
                nom_produit=str(row["Name"]),
                option_taille=str(row.get("Attribute 2 value(s)", "")).strip(),
                couleurs_detectees=[
                    c.strip()
                    for c in row.get("Couleurs détectées", "").split(",")
                    if c.strip()
                ],
            ),
            axis=1,
        )

        df_variables_reels = df[df["Is_Variable"]]
        print(f"✅ Produits variables réellement éligibles : {len(df_variables_reels)}")

        # 🧪 Log de débogage des groupes
        print("\n🧪 Aperçu des regroupements prévus :")
        for i, (name, group) in enumerate(df_variables_reels.groupby("Name")):
            print(f"  {i+1}. {name} ({len(group)} produits)")

        # Regroupement
        if not df_variables_reels.empty:
            df_final = regrouper_variations_par_taille_et_couleur(df_variables_reels)
            print(f"\n✅ Produits regroupés (taille + couleur) : {len(df_final)}")
        else:
            df_final = pd.DataFrame()
            print("ℹ️ Aucun produit variable éligible trouvé.")

        df_final.drop(
            columns=["Taille détectée", "Couleurs détectées"],
            errors="ignore",
            inplace=True,
        )

        # ✅ Correction ici : applique le nettoyage sur la colonne uniquement
        df_final["Name"] = df_final["Name"].apply(nettoyer_nom_pour_parent)

        nouveau_chemin = os.path.splitext(chemin_fichier)[0] + "_final.csv"
        df_final.to_csv(nouveau_chemin, index=False, sep=",", encoding="utf-8-sig")
        print(f"\n✅ Fichier final exporté avec succès : {nouveau_chemin}")

    except Exception as e:
        print(f"❌ Erreur pendant le traitement : {e}")


if __name__ == "__main__":
    main()

