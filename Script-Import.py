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

def generer_sku_et_ean_fallback(row, index=None):
    sku = str(row.get("SKU", "")).strip()
    if not sku:
        sku = str(row.get("stock - identifiant", "")).strip()
    if not sku:
        sku = f"GENERICSKU-{index}" if index is not None else "GENERICSKU"

    ean = str(row.get("Code EAN", "")).strip()
    if not ean:
        ean = str(row.get("stock - EAN", "")).strip()
    if not ean:
        ean = f"GENERICEAN-{index}" if index is not None else "GENERICEAN"

    return sku, ean

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

    df["all_image_urls"] = df[colonnes_existantes].apply(
        lambda row: [base_url + img.strip() for img in row.dropna().astype(str)], axis=1
    )

    df["Images"] = df["all_image_urls"].apply(lambda urls: ", ".join(urls))

    # Cette ligne doit être ici, bien alignée avec les autres
    toutes_urls = list(set(url for sublist in df["all_image_urls"] for url in sublist))

    url_to_id = recuperer_id_images_wp_via_api_batch(toutes_urls, taille_lot)

    def generer_meta(row):
        urls_sup = row["all_image_urls"][1:]
        ids_sup = [str(url_to_id[url]) for url in urls_sup if url in url_to_id]
        return ",".join(ids_sup)

    df["_wc_additional_variation_images"] = df.apply(generer_meta, axis=1)

    df.drop(
        columns=colonnes_existantes + ["all_image_urls"], inplace=True, errors="ignore"
    )

    return df


# --- 👇 Fonction API désactivée mais conservée si besoin futur ---
def recuperer_id_images_wp_via_api_batch(urls, taille_lot=100):
    api_url = "https://dev.yolobaby.online/api-images.php"
    url_to_id = {}

    for i in range(0, len(urls), taille_lot):
        lot_urls = urls[i:i + taille_lot]
        try:
            response = requests.post(
                api_url,
                json={"urls": lot_urls, "api_key": "12345"},
                timeout=10
            )
            response.raise_for_status()
            resultat = response.json()
            url_to_id.update(resultat)
            print(f"✅ Lot {i // taille_lot + 1}/{(len(urls) - 1) // taille_lot + 1} traité avec succès.")

        except requests.RequestException as e:
            print(f"❌ Erreur API sur le lot {i // taille_lot + 1}: {e}")

            # Essayer de récupérer une réponse textuelle si possible
            try:
                print("Réponse API :", response.text)
            except NameError:
                print("⚠️ Aucune réponse n’a été reçue (response non définie).")
            except Exception as ex:
                print(f"⚠️ Impossible d’afficher la réponse : {ex}")

            sleep(1)  # Pause pour éviter surcharge serveur

    return url_to_id



def convertir_en_json(val, stock):
    if pd.isna(val) or not isinstance(val, str):
        return ""
    val = val.replace("\n", "").replace("\r", "").strip()
    if ";" in val:
        title, stock_location = map(str.strip, val.split(";", 1))
    else:
        title, stock_location = val.strip(), ""
    try:
        stock_int = int(float(stock)) if pd.notna(stock) else 0
    except:
        stock_int = 0
    return json.dumps(
        [{"title": title, "stock": stock_int, "stock_location": stock_location}],
        ensure_ascii=False,
    )


def transformer_emplacements_en_inventaire(df):
    grouped_inventories = defaultdict(list)

    for idx, row in df.iterrows():
        try:
            sku = str(row.get("SKU", "")).strip()
            if not sku:
                sku = str(row.get("stock - identifiant", "")).strip()
            if not sku:
                continue  # Toujours ignorer si aucun identifiant exploitable

            emplacement_raw = str(
                row.get("Méta : stock - emplacement de stockage", "")
            ).strip()
            stock = row.get("Stock", "0")

            if not emplacement_raw or emplacement_raw.lower() in ["", "nan", "none"]:
                continue

            if ";" in emplacement_raw:
                title, stock_location = map(str.strip, emplacement_raw.split(";", 1))
            else:
                title, stock_location = emplacement_raw, ""

            try:
                stock_val = int(float(stock))
            except:
                stock_val = 0

            inventory = {
                "title": title,
                "stock": stock_val,
                "stock_location": stock_location,
            }

            grouped_inventories[sku].append(inventory)

        except Exception as e:
            print(
                f"❌ Erreur ligne {idx} dans transformer_emplacements_en_inventaire (SKU: {row.get('SKU', '')}): {e}"
            )
            continue

    rows = []
    for sku, inventories in grouped_inventories.items():
        rows.append(
            {
                "SKU": sku,
                "_mi_inventory_data": json.dumps(inventories, ensure_ascii=False),
            }
        )

    return pd.DataFrame(rows)


#
############################################
# Fonctions de détection/extraction des couleurs
############################################


def detecter_toutes_couleurs(nom_produit: str):
    if not isinstance(nom_produit, str):
        return []

    tokens = re.split(r"[\s\-\|\(\),/]+", nom_produit.lower())
    trouvees = [mapping_couleurs[t] for t in tokens if t in mapping_couleurs]

    return list(dict.fromkeys(trouvees))  # Supprime les doublons


# 📌 Fonction pour normaliser une liste de couleurs
def normaliser_liste_couleurs(couleurs_brutes: list):
    if not couleurs_brutes:
        return ""
    return ", ".join(
        dict.fromkeys(
            [
                mapping_couleurs.get(c.lower(), "Non spécifiée").title()
                for c in couleurs_brutes
            ]
        )
    )


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
        r"\b\d{1,2}\s?[-àa]\s?\d{1,2}\s?(mois|ans|kg|m|a)\b",
        r"\b(?:\+|\d{1,2})\s?(mois|ans)\b",
        r"\b(?:taille\s?)?(\d{1,2}[+]?)\b",
        r"\b(\d{3,4})\s?(g|grammes|kg)\b",
        r"\b(premier|1er|2eme|2e|3eme|3e)\s?age\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, texte)
        if match:
            return match.group(0).strip()

    return ""


# 📌 Fonction pour nettoyer le nom du produit en supprimant la couleur
def nettoyer_nom_produit(nom_produit: str, couleurs: list):
    if not isinstance(nom_produit, str):
        return nom_produit
    # On retire d'abord les couleurs (s'il y en a) en tant que mots entiers
    for couleur in couleurs:
        nom_produit = re.sub(rf"\b{couleur}\b", "", nom_produit, flags=re.IGNORECASE)
    # Puis, si le nom contient " - ", on prend uniquement la partie avant
    if " - " in nom_produit:
        nom_produit = nom_produit.split(" - ")[0]
    # Enfin, on nettoie les espaces superflus et d'éventuels tirets en fin de chaîne
    nom_produit = re.sub(r"[-\s]+$", "", nom_produit)
    return re.sub(r"\s+", " ", nom_produit).strip()


# Renvoie un dictionnaire contenant les couleurs détectées
def determiner_si_variable(nom_produit: str, option_taille: str = ""):
    """
    Un produit est variable s’il :
    - contient exactement une couleur détectée dans son nom
    - ou s’il a une taille détectée via un pattern intelligent
    """
    couleurs_detectees = detecter_toutes_couleurs(nom_produit)

    # Sécurisation max ici 👇
    taille = str(option_taille).strip().lower() if pd.notnull(option_taille) else ""

    contient_taille = bool(re.search(r"(mois|ans|m|t)", taille)) and len(taille) <= 10

    return len(couleurs_detectees) == 1 or contient_taille


# 📌 Fonction pour regrouper les produits **variables** par couleur


def regrouper_variations_par_taille(df):
    groupes = {}

    for idx, row in df.iterrows():
        try:
            nom_original = str(row["Name"])
            taille_raw = row.get("Attribute 2 value(s)", "")
            taille = str(taille_raw).strip() if pd.notnull(taille_raw) else ""
            nom_base = re.sub(rf"\b{re.escape(taille)}\b", "", nom_original, flags=re.IGNORECASE).strip()
            groupes.setdefault(nom_base.lower(), []).append((idx, row.to_dict()))
        except Exception as e:
            print(f"❌ Erreur ligne {idx} dans regroupement par taille (SKU: {row.get('SKU', '')}): {e}")
            continue

    liste_resultats = []

    for ref, lignes in groupes.items():
        tailles_group = set()
        idx0, base_row = lignes[0]
        sku_orig, ean_orig = generer_sku_et_ean_fallback(base_row, index=idx0)

        for _, row in lignes:
            taille = str(row.get("Attribute 2 value(s)", "")).strip()
            if taille:
                tailles_group.add(taille)

        tailles_group_list = sorted(list(tailles_group))

        parent = base_row.copy()
        parent["SKU"] = "PARENT-" + sku_orig
        parent["Type"] = "variable"
        parent["Attribute 2 name"] = "Taille"
        parent["Attribute 2 value(s)"] = ", ".join(tailles_group_list)
        parent["Attribute 2 visible"] = "yes"
        parent["Attribute 2 global"] = "yes"
        parent["Parent SKU"] = ""
        parent["Code EAN"] = ""
        liste_resultats.append(parent)

        for idx, row in lignes:
            variation = row.copy()
            variation["Type"] = "variation"
            variation["Parent SKU"] = parent["SKU"]
            variation["Attribute 2 name"] = "Taille"
            taille = str(variation.get("Attribute 2 value(s)", "")).strip()
            variation["Attribute 2 value(s)"] = taille
            variation["Attribute 2 visible"] = "yes"
            variation["Attribute 2 global"] = "yes"

            if not variation.get("SKU"):
                variation["SKU"] = sku_orig
            if not variation.get("Code EAN"):
                variation["Code EAN"] = ean_orig

            liste_resultats.append(variation)

    return pd.DataFrame(liste_resultats)


def regrouper_variations_par_couleur(df):
    groupes = {}

    for idx, row in df.iterrows():
        try:
            nom_original = str(row["Name"])
            couleurs_detectees = detecter_toutes_couleurs(nom_original)
            nom_sans_couleur = nettoyer_nom_produit(nom_original, couleurs_detectees).strip()
            key = nom_sans_couleur.lower()
            groupes.setdefault(key, []).append((idx, row.to_dict()))
        except Exception as e:
            print(f"❌ Erreur ligne {idx} dans regroupement par couleur (SKU: {row.get('SKU', '')}): {e}")
            continue

    liste_resultats = []

    for key, lignes in groupes.items():
        couleurs_group = set()
        for _, row in lignes:
            couleurs_group.update(detecter_toutes_couleurs(str(row.get("Name", ""))))

        couleurs_group_list = list(couleurs_group)

        idx0, base_row = lignes[0]
        sku_orig, ean_orig = generer_sku_et_ean_fallback(base_row, index=idx0)

        if len(lignes) == 1 and len(couleurs_group_list) == 1:
            parent = base_row.copy()
            variation = base_row.copy()

            parent["SKU"] = "PARENT-" + sku_orig
            parent["Name"] = nettoyer_nom_produit(parent["Name"], couleurs_group_list)
            parent["Type"] = "variable"
            parent["Attribute 1 name"] = "Couleur"
            parent["Attribute 1 value(s)"] = normaliser_liste_couleurs(couleurs_group_list)
            parent["Attribute 1 visible"] = "yes"
            parent["Attribute 1 global"] = "yes"
            parent["Code EAN"] = ""
            parent["Parent SKU"] = ""
            liste_resultats.append(parent)

            variation["Type"] = "variation"
            variation["Parent SKU"] = parent["SKU"]
            variation["Attribute 1 name"] = "Couleur"
            variation["Attribute 1 value(s)"] = normaliser_liste_couleurs(couleurs_group_list)
            variation["Attribute 1 visible"] = "yes"
            variation["Attribute 1 global"] = "yes"
            variation["SKU"] = sku_orig
            variation["Code EAN"] = ean_orig
            liste_resultats.append(variation)

        elif len(lignes) > 1:
            parent = base_row.copy()
            parent["SKU"] = "PARENT-" + sku_orig
            parent["Name"] = nettoyer_nom_produit(parent["Name"], couleurs_group_list)
            parent["Type"] = "variable"
            parent["Attribute 1 name"] = "Couleur"
            parent["Attribute 1 value(s)"] = normaliser_liste_couleurs(couleurs_group_list)
            parent["Attribute 1 visible"] = "yes"
            parent["Attribute 1 global"] = "yes"
            parent["Code EAN"] = ""
            parent["Parent SKU"] = ""
            liste_resultats.append(parent)

            for idx, row in lignes:
                variation = row.copy()
                variation["Type"] = "variation"
                variation["Parent SKU"] = parent["SKU"]
                var_couleurs = detecter_toutes_couleurs(str(variation["Name"]))
                variation["Attribute 1 name"] = "Couleur"
                variation["Attribute 1 value(s)"] = normaliser_liste_couleurs(var_couleurs)
                variation["Attribute 1 visible"] = "yes"
                variation["Attribute 1 global"] = "yes"

                if not variation.get("SKU"):
                    variation["SKU"] = sku_orig
                if not variation.get("Code EAN"):
                    variation["Code EAN"] = ean_orig

                liste_resultats.append(variation)

        else:
            print(f"ℹ️ Groupe ignoré (pas de couleur détectée) : {key}")

    return pd.DataFrame(liste_resultats)


def main():
    root = Tk()
    root.withdraw()

    chemin_fichier = filedialog.askopenfilename(
        filetypes=[("CSV Files", "*.csv")],
        title="Sélectionnez le fichier CSV"
    )
    if not chemin_fichier:
        print("❌ Aucun fichier sélectionné. Fermeture du script.")
        return

    try:
        df = pd.read_csv(chemin_fichier, encoding="utf-8-sig", dtype=str)
        print(f"🟢 ÉTAPE 1 — CSV chargé : {os.path.basename(chemin_fichier)}")

        df.columns = df.columns.str.strip()

        if "Stock - Quantité" in df.columns:
            df.rename(columns={"Stock - Quantité": "Stock"}, inplace=True)

        colonnes_dupliquees = df.columns[df.columns.duplicated()].tolist()
        if colonnes_dupliquees:
            print(f"⚠️ Colonnes dupliquées détectées : {colonnes_dupliquees}")
            df = df.loc[:, ~df.columns.duplicated()]
            print("✅ Colonnes dupliquées supprimées.")

        print("🟢 ÉTAPE 3 — Génération _mi_inventory_data")
        if "Stock - Emplacement de stockage" in df.columns and "Stock" in df.columns:
            def convertir_en_json_sécurisé(row):
                try:
                    val = row.get("Stock - Emplacement de stockage", "")
                    stock = row.get("Stock", "0")
                    return convertir_en_json(val, stock)
                except Exception as e:
                    print(f"❌ Erreur JSON Stock (SKU: {row.get('SKU', '')}) : {e}")
                    return ""
            df["_mi_inventory_data"] = df.apply(convertir_en_json_sécurisé, axis=1)
            print("✅ Colonne _mi_inventory_data générée.")
        else:
            print("⚠️ Colonnes manquantes pour ATUM. Saut du traitement.")

        print("🟢 ÉTAPE 4 — Renommage colonnes WooCommerce")
        df = renommer_colonnes_pour_woocommerce(df)

        if "Name" not in df.columns:
            raise KeyError("❌ Colonne 'Name' absente !")

        if "Attribute 2 value(s)" not in df.columns:
            df["Attribute 2 value(s)"] = ""

        df["Attribute 2 value(s)"] = df["Attribute 2 value(s)"].fillna("").astype(str).apply(str.strip)
        df = supprimer_doublons_colonnes(df)
        df = ajuster_categories(df)

        print("🟢 ÉTAPE 5 — Formatter images")
        df = formatter_images(df, taille_lot=50)

        if not df.index.is_unique:
            print("⚠️ Index dupliqué après formatter_images() → reset.")
            df = df.reset_index(drop=True)

        print("🟢 ÉTAPE 6 — Préparation détection variables")
        df["Attribute 2 value(s)"] = df.apply(
            lambda row: row["Attribute 2 value(s)"]
            if row["Attribute 2 value(s)"].strip()
            else detecter_taille_dans_nom(row["Name"]),
            axis=1
        )

        df["Is_Variable"] = df.apply(
            lambda row: determiner_si_variable(
                str(row["Name"]),
                str(row.get("Attribute 2 value(s)", "")).strip()
            ),
            axis=1
        )

        df_variables_reels = df[df["Is_Variable"]]
        print(f"✅ Produits variables : {len(df_variables_reels)}")

        print("🟢 ÉTAPE 7 — Groupements taille/couleur")
        df_has_size = df_variables_reels[
            df_variables_reels["Attribute 2 value(s)"].notna() &
            (df_variables_reels["Attribute 2 value(s)"].str.strip() != "")
        ]
        df_without_size = df_variables_reels[
            df_variables_reels["Attribute 2 value(s)"].isna() |
            (df_variables_reels["Attribute 2 value(s)"].str.strip() == "")
        ]

        df_grouped_size = regrouper_variations_par_taille(df_has_size) if not df_has_size.empty else pd.DataFrame()
        df_grouped_color = regrouper_variations_par_couleur(df_without_size) if not df_without_size.empty else pd.DataFrame()

        print("📊 Vérification des index AVANT concaténation :")
        if not df_grouped_size.empty:
            print(f" - df_grouped_size shape : {df_grouped_size.shape}")
            print(f" - Index unique ? {df_grouped_size.index.is_unique}")
            print(f" - Duplicates dans index : {df_grouped_size.index.duplicated().sum()}")
            df_grouped_size.index = pd.RangeIndex(len(df_grouped_size))

        if not df_grouped_color.empty:
            print(f" - df_grouped_color shape : {df_grouped_color.shape}")
            print(f" - Index unique ? {df_grouped_color.index.is_unique}")
            print(f" - Duplicates dans index : {df_grouped_color.index.duplicated().sum()}")
            df_grouped_color.index = pd.RangeIndex(len(df_grouped_color))

        print("🟢 ÉTAPE 8 — Concaténation des produits variables")
        df_final = pd.concat([df_grouped_size, df_grouped_color], ignore_index=True)
        df_final.index = pd.RangeIndex(len(df_final))  # 🔐 Anti-crash index

        print("🟢 ÉTAPE 9 — Nettoyage final avant export")
        df_final.drop_duplicates(subset=["SKU", "Name", "Attribute 2 value(s)"], inplace=True)
        df_final = df_final.reset_index(drop=True)
        df_final["SKU"] = df_final["SKU"].astype(str).str.strip()

        nouveau_chemin = os.path.splitext(chemin_fichier)[0] + "_final.csv"
        df_final.to_csv(nouveau_chemin, index=False, sep=",", encoding="utf-8-sig")
        print(f"✅ Fichier final exporté : {nouveau_chemin}")

    except Exception as e:
        print(f"❌ Erreur pendant le traitement : {e}")


if __name__ == "__main__":
    main()
