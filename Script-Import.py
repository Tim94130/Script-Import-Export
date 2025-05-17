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


def formatter_images(df):
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

    cols = [c for c in colonnes_images if c in df.columns]
    if not cols:
        print("⚠️ Aucune colonne d'image trouvée.")
        return df

    # Concatène directement les URLs dans la colonne Images
    df["Images"] = df[cols] \
        .apply(lambda row: ", ".join(base_url + img.strip() for img in row.dropna().astype(str)), axis=1)

    # Supprime les colonnes source
    df.drop(columns=cols, inplace=True, errors="ignore")
    return df


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
    couleur = extraire_couleur_libre(nom_produit)
    return [couleur] if couleur else []

def extraire_couleur_libre(nom_produit: str, debug=False):
    """
    Extrait une couleur depuis le nom du produit.
    Cherche une couleur de base dans toute la chaîne,
    puis tente de l'enrichir avec l'adjectif devant ou derrière,
    même après un tiret ou dans des groupes de mots.
    """

    if not isinstance(nom_produit, str):
        return ""

    # Nettoyage Unicode et suppression de la marque après |
    texte = unicodedata.normalize("NFKD", nom_produit).encode("ascii", "ignore").decode("utf-8")
    texte = texte.split("|")[0].strip()

    # Ne découpe pas brutalement au tiret, mais conserve les blocs de mots
    blocs = re.split(r"[/,]+", texte)
    mots = []
    for bloc in blocs:
        sous_mots = bloc.strip().split()
        mots.extend(sous_mots)

    mots_bas = [m.lower() for m in mots]

    couleurs_base = {
        "white", "black", "brown", "blue", "red", "pink", "green",
        "grey", "gray", "yellow", "orange", "purple", "beige",
        "gold", "silver", "cyan", "magenta", "navy", "maroon",
        "lime", "olive", "teal", "aqua", "blanc", "noir", "marron", "brun",
        "bleu", "rouge", "rose", "vert", "gris", "jaune", "violet", "kaki",
        "doré", "argent", "turquoise", "fuchsia", "lavande", "sable",
        "prune", "sepia", "chocolat"
    }

    mots_interdits = {
        "eco", "base", "fix", "t", "pack", "set", "lot", "urban", "mobility", "plus", "confort",
        "ans", "mois", "age", "taille", "tissu", "i-size", "kg", "cm", "g", "isofix", "pivot",
        "line", "size", "tissus", "pour", "de", "avec", "sans", "one", "solution", "insert", "sirona", "cloud"
    }.union(set(str(i) for i in range(0, 3000)))

    for i, mot in enumerate(mots_bas):
        if mot in couleurs_base:
            # Récupère un adjectif éventuel avant ou après
            adj_avant = mots[i - 1] if i > 0 and mots_bas[i - 1] not in mots_interdits else ""
            adj_apres = mots[i + 1] if i + 1 < len(mots) and mots_bas[i + 1] not in mots_interdits else ""
            if adj_avant:
                couleur = f"{adj_avant} {mots[i]}"
            elif adj_apres:
                couleur = f"{mots[i]} {adj_apres}"
            else:
                couleur = mots[i]
            if debug:
                print(f"🎨 Couleur détectée : '{couleur}' dans '{nom_produit}'")
            return couleur.strip()

    if debug:
        print(f"🚫 Aucune couleur détectée dans : '{nom_produit}'")
    return ""




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

    for couleur in couleurs:
        try:
            couleur_safe = re.escape(couleur)
            nouveau_nom = re.sub(rf"\b{couleur_safe}\b", "", nom_produit, flags=re.IGNORECASE)
            if nouveau_nom != nom_produit:
                print(f"🧹 Suppression de la couleur '{couleur}' dans : {nom_produit}")
            nom_produit = nouveau_nom
        except Exception as e:
            print(f"❌ Erreur lors du nettoyage de la couleur '{couleur}' : {e}")

    if " - " in nom_produit:
        nom_produit = nom_produit.split(" - ")[0]

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
    """
    Regroupe les produits par nom sans taille. Chaque groupe est traité comme un produit variable,
    même s’il contient une seule variation.
    """
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

    for key, lignes in groupes.items():
        tailles_group = set()
        for _, row in lignes:
            taille = str(row.get("Attribute 2 value(s)", "")).strip()
            if taille:
                tailles_group.add(taille)

        tailles_group_list = sorted(tailles_group)
        idx0, base_row = lignes[0]
        sku_orig, ean_orig = generer_sku_et_ean_fallback(base_row, index=idx0)

        # ➕ Produit parent
        parent = base_row.copy()
        parent["SKU"] = "PARENT-" + sku_orig
        parent["Name"] = nettoyer_nom_produit(parent["Name"], tailles_group_list)
        parent["Type"] = "variable"
        parent["Attribute 2 name"] = "Taille"
        parent["Attribute 2 value(s)"] = ", ".join(tailles_group_list)
        parent["Attribute 2 visible"] = "yes"
        parent["Attribute 2 global"] = "yes"
        parent["Code EAN"] = ""
        parent["Parent SKU"] = ""
        liste_resultats.append(parent)

        # ➕ Variations (même s’il n’y en a qu’une)
        for idx, row in lignes:
            variation = row.copy()
            taille = str(variation.get("Attribute 2 value(s)", "")).strip()

            variation["Type"] = "variation"
            variation["Parent SKU"] = parent["SKU"]
            variation["Attribute 2 name"] = "Taille"
            variation["Attribute 2 value(s)"] = taille
            variation["Attribute 2 visible"] = "yes"
            variation["Attribute 2 global"] = "yes"

            if not variation.get("SKU"):
                variation["SKU"], _ = generer_sku_et_ean_fallback(variation, index=idx)
            if not variation.get("Code EAN"):
                _, variation["Code EAN"] = generer_sku_et_ean_fallback(variation, index=idx)

            liste_resultats.append(variation)

    return pd.DataFrame(liste_resultats)



def regrouper_variations_par_couleur(df):
    """
    Regroupe les produits par nom sans couleur. Chaque groupe devient un produit variable,
    même s’il n’a qu’un seul élément.
    """
    groupes = {}

    for idx, row in df.iterrows():
        try:
            nom_original = str(row["Name"])
            couleur_extraite = extraire_couleur_libre(nom_original)
            nom_sans_couleur = nettoyer_nom_produit(nom_original, [couleur_extraite]).strip()
            key = nom_sans_couleur.lower()
            groupes.setdefault(key, []).append((idx, row.to_dict()))
        except Exception as e:
            print(f"❌ Erreur ligne {idx} dans regroupement par couleur (SKU: {row.get('SKU', '')}): {e}")
            continue

    liste_resultats = []

    for key, lignes in groupes.items():
        couleurs_group = set()
        for _, row in lignes:
            couleur = extraire_couleur_libre(row.get("Name", ""))
            if couleur:
                couleurs_group.add(couleur)

        couleurs_group_list = list(couleurs_group)
        idx0, base_row = lignes[0]
        sku_orig, ean_orig = generer_sku_et_ean_fallback(base_row, index=idx0)

        # ➕ Produit parent
        parent = base_row.copy()
        parent["SKU"] = "PARENT-" + sku_orig
        parent["Name"] = nettoyer_nom_produit(parent["Name"], couleurs_group_list)
        parent["Type"] = "variable"
        parent["Attribute 1 name"] = "Couleur"
        parent["Attribute 1 value(s)"] = ", ".join(couleurs_group_list)
        parent["Attribute 1 visible"] = "yes"
        parent["Attribute 1 global"] = "yes"
        parent["Code EAN"] = ""
        parent["Parent SKU"] = ""
        liste_resultats.append(parent)

        # ➕ Variations (même s’il n’y en a qu’une)
        for idx, row in lignes:
            variation = row.copy()
            couleur = extraire_couleur_libre(variation.get("Name", ""))
            variation["Type"] = "variation"
            variation["Parent SKU"] = parent["SKU"]
            variation["Attribute 1 name"] = "Couleur"
            variation["Attribute 1 value(s)"] = couleur
            variation["Attribute 1 visible"] = "yes"
            variation["Attribute 1 global"] = "yes"

            if not variation.get("SKU"):
                variation["SKU"], _ = generer_sku_et_ean_fallback(variation, index=idx)
            if not variation.get("Code EAN"):
                _, variation["Code EAN"] = generer_sku_et_ean_fallback(variation, index=idx)

            liste_resultats.append(variation)

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
        
        print("🟢 ÉTAPE 4 — Renommage colonnes WooCommerce")
        df = renommer_colonnes_pour_woocommerce(df)

        if "Name" not in df.columns:
            raise KeyError("❌ Colonne 'Name' absente !")

        if "Attribute 2 value(s)" not in df.columns:
            df["Attribute 2 value(s)"] = ""

        df["Attribute 2 value(s)"] = (
            df["Attribute 2 value(s)"]
            .fillna("")
            .astype(str)
            .apply(str.strip)
        )
        df = supprimer_doublons_colonnes(df)
        df = ajuster_categories(df)

        print("🟢 ÉTAPE 5 — Formatter images")
        df = formatter_images(df)  # plus de taille_lot

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

        df_grouped_size = (
            regrouper_variations_par_taille(df_has_size)
            if not df_has_size.empty else pd.DataFrame()
        )
        df_grouped_color = (
            regrouper_variations_par_couleur(df_without_size)
            if not df_without_size.empty else pd.DataFrame()
        )

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
        df_final.index = pd.RangeIndex(len(df_final))

        print("🟢 ÉTAPE 9 — Nettoyage final avant export")
        df_final.drop_duplicates(
            subset=["SKU", "Name", "Attribute 2 value(s)"],
            inplace=True
        )
        df_final = df_final.reset_index(drop=True)
        df_final["SKU"] = df_final["SKU"].astype(str).str.strip()

        nouveau_chemin = os.path.splitext(chemin_fichier)[0] + "_final.csv"
        df_final.to_csv(nouveau_chemin, index=False, sep=",", encoding="utf-8-sig")
        print(f"✅ Fichier final exporté : {nouveau_chemin}")

    except Exception as e:
        print(f"❌ Erreur pendant le traitement : {e}")


if __name__ == "__main__":
    main()
