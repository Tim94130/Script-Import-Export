# Importation des bibliothèques nécessaires
import pandas as pd
from tkinter import Tk, filedialog
import os
import re
import json
import unicodedata
from collections import defaultdict
from rapidfuzz import process, fuzz  # Si nécessaireimport csv
import csv
import MySQLdb


# Définitions globales pour la détection des couleurs
adjectifs_ignores = [
    "dark", "light", "pale", "deep", "bright", "medium",
    "fonce", "foncé", "clair", "pâle", "flashy", "fluorescent"
]

couleurs_base = [
    "white", "black", "brown", "blue", "red", "pink", "green", 
    "grey", "gray", "yellow", "orange", "purple", "violet",
    "beige", "gold", "silver", "taupe", "cyan", "magenta",
    "navy", "maroon", "lime", "olive", "teal", "aqua",
    "blanc", "noir", "marron", "brun", "bleu", "rouge", "rose", 
    "vert", "gris", "jaune", "violet", "beige", "doré", "argent", "kaki",
    "turquoise", "fuchsia", "lavande", "ocre", "ivory", "ivoires", "argenté",
    "rose gold", "off white", "peach pink", "sepia black", "golden",
    "sable", "chocolat", "prune" ,"dark brown"
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
    
    "teal": "Bleu-vert"
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
        "Marque": "Brands"
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
        "Marque": "Brands"
    }
    colonnes_presentes = df.columns
    colonnes_a_supprimer = [
        fr_col for fr_col, en_col in correspondance_woocommerce.items() 
        if fr_col in colonnes_presentes and en_col in colonnes_presentes
    ]
    df.drop(columns=colonnes_a_supprimer, inplace=True, errors='ignore')
    return df

def ajuster_categories(df):
    colonnes_categories = [
        'Nom de la catégorie de niveau 1 (en Français)',
        'Nom de la catégorie de niveau 2 (en Français)',
        'Nom de la catégorie de niveau 3 (en Français)',
        'Nom de la catégorie de niveau 4 (en Français)',
    ]
    colonnes_existantes = [col for col in colonnes_categories if col in df.columns]
    if colonnes_existantes:
        df['Categories'] = df[colonnes_existantes].apply(lambda x: ' > '.join(x.dropna()), axis=1)
    if 'Catégorie principale du produit' in df.columns:
        df['Categories'] = df.apply(
            lambda x: f"{x['Categories']} | {x['Catégorie principale du produit']}" 
            if pd.notnull(x['Catégorie principale du produit']) else x['Categories'],
            axis=1
        )
    df.drop(columns=colonnes_existantes + ['Catégorie principale du produit'], inplace=True, errors='ignore')
    return df

def formatter_images(df):
    base_url = "http://yolobaby.online/wp-content/uploads/image-site/"
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
        "Image supplémentaire n°9"
    ]
    colonnes_existantes = [col for col in colonnes_images if col in df.columns]
    if not colonnes_existantes:
        print("⚠️ Aucune colonne d'image trouvée, la colonne 'Images' ne sera pas créée.")
        return df
    
    df['Images'] = df[colonnes_existantes].apply(
        lambda row: ", ".join([base_url + img.strip() for img in row.dropna().astype(str)]),
        axis=1
    )
    print("🔍 Vérification des images fusionnées avec URLs complètes :")
    print(df[['SKU', 'Images']].head())
    
    if df['Images'].isnull().all():
        print("⚠️ Aucune image fusionnée, les colonnes originales ne seront pas supprimées.")
    else:
        print("✅ Fusion des images réussie avec URLs, suppression des colonnes d'origine.")
        df.drop(columns=colonnes_existantes, inplace=True, errors='ignore')
    
    return df

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
    return ", ".join(dict.fromkeys([mapping_couleurs.get(c.lower(), "Non spécifiée").title() for c in couleurs_brutes]))

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
    nom_produit = re.sub(r'[-\s]+$', '', nom_produit)
    return re.sub(r'\s+', ' ', nom_produit).strip()

# 📌 Fonction pour détecter les produits composites
def extraire_couleurs_composite(nom_produit: str):
    """
    Extrait les couleurs liées aux éléments "Châssis" et "Siège".
    Un produit est considéré composite s'il a **Châssis** et **Siège** dans le même nom.
    """

    if not isinstance(nom_produit, str):
        return {}

    # Normalisation du texte (supprimer accents et mettre en minuscule)
    nom_lower = unicodedata.normalize("NFKD", nom_produit).encode("ASCII", "ignore").decode("utf-8").lower()
    resultat = {}

    # Définition des éléments à rechercher
    elements_couleur = {
        "Châssis": ["châssis", "chassis"],
        "Siège": ["siège", "siege", "assise"]
    }

    # Vérification de la présence des deux termes dans le même nom de produit
    contient_chassis = any(mot in nom_lower for mot in elements_couleur["Châssis"])
    contient_siege = any(mot in nom_lower for mot in elements_couleur["Siège"])

    if not (contient_chassis and contient_siege):
        return {}  # Pas un produit composite

    # Définition des adjectifs ignorés
    adjectifs_ignores = [
    "light", "pale", "deep", "bright", "medium",
    "fonce", "foncé", "clair", "pâle", "flashy", "fluorescent",
    "cozy", "mirage", "sepia", "peach", "magic", "canvas", "navy"
    "fog", "stormy", "almond", "leaf", "navy","candy", "fog", "almond", "canvas"
    
    # Ajout des adjectifs liés au Châssis
    "chrome", "matt", "matté", "brillant", "argenté", "dark", "magic"
    ]

    # Recherche des couleurs pour chaque élément
    for nom_element, variantes in elements_couleur.items():
        for variante in variantes:
            # Correction du regex pour éviter l'erreur "no such group"
            regex_patterns = [
                rf"{variante}\s+(?:({'|'.join(adjectifs_ignores)})\s+)?({'|'.join(couleurs_base)})",
                rf"({'|'.join(couleurs_base)})\s+{variante}"
            ]
            for regex in regex_patterns:
                match = re.search(regex, nom_lower, re.IGNORECASE)
                if match:
                    # Vérification si l'adjectif est capturé
                    couleur_brute = match.group(2) if match.lastindex == 2 else match.group(1)
                    couleur_normalisee = mapping_couleurs.get(couleur_brute, couleur_brute).title()
                    resultat[nom_element] = couleur_normalisee
                    break  # Sortir dès qu'une couleur est trouvée

    return resultat

  # Renvoie un dictionnaire contenant les couleurs détectées
def determiner_si_variable(nom_produit: str):
    """
    Détermine si un produit est variable en fonction du nombre de couleurs détectées dans son nom.
    Un produit est variable **s'il contient une seule couleur dans son nom**.
    """
    couleurs_detectees = detecter_toutes_couleurs(nom_produit)
    return len(couleurs_detectees) == 1

# 📌 Fonction pour regrouper les produits **variables** par couleur


def regrouper_variations_par_couleur(df):
    """
    Regroupe les produits par modèle (basé sur le nom nettoyé sans couleur).

    - Si le groupe ne présente qu'une seule couleur, le produit est importé comme produit simple.
    - Sinon, on génère :
        • Un produit parent (Type = "variable") créé à partir du premier produit du groupe.
          Son SKU est modifié en ajoutant le préfixe "PARENT-".
          Son nom est nettoyé (les couleurs et séparateurs superflus sont retirés).
          Son "Attribute 1 value(s)" contient l'union de toutes les couleurs du groupe.
          Le champ "Code EAN" est vidé et "Parent SKU" est vide.
        • Une ligne variation pour chaque produit du groupe (même celui utilisé pour le parent).
          Chaque variation conserve son nom complet (avec la couleur) et renseigne "Parent SKU" avec le SKU du parent.
          Pour la variation issue du produit utilisé pour le parent (qui aurait le même SKU d'origine),
          on modifie son SKU (par exemple en ajoutant un suffixe basé sur la couleur) pour garantir l'unicité.
    """
    # 1) Regrouper par nom nettoyé (sans couleur)
    groupes = {}
    for _, row in df.iterrows():
        nom_original = str(row["Name"])
        couleurs_detectees = detecter_toutes_couleurs(nom_original)
        nom_sans_couleur = nettoyer_nom_produit(nom_original, couleurs_detectees).strip()
        key = nom_sans_couleur.lower()
        groupes.setdefault(key, []).append(row)
    
    liste_resultats = []

    # 2) Traiter chaque groupe
    for key, rows in groupes.items():
        # a) Agréger toutes les couleurs du groupe
        couleurs_group = set()
        for row in rows:
            couleurs = detecter_toutes_couleurs(str(row["Name"]))
            couleurs_group.update(couleurs)
        couleurs_group_list = list(couleurs_group)
        
        # Si le groupe ne présente qu'une seule couleur, importer comme produit simple
        if len(couleurs_group_list) == 1:
            simple_product = rows[0].copy()
            simple_product["Type"] = "simple"
            simple_product["Attribute 1 name"] = "Couleur"
            simple_product["Attribute 1 value(s)"] = normaliser_liste_couleurs(couleurs_group_list)
            simple_product["Attribute 1 visible"] = "yes"
            simple_product["Attribute 1 global"] = "yes"
            simple_product["Parent SKU"] = ""
            # On ne modifie pas le SKU ni le Code EAN pour un produit simple (ou on peut vider l'EAN si souhaité)
            liste_resultats.append(simple_product)
        else:
            # b) Sinon, créer un produit parent et des variations
            # Création du parent à partir du premier produit du groupe
            parent = rows[0].copy()
            sku_orig = str(parent["SKU"])
            parent["SKU"] = "PARENT-" + sku_orig  # modification du SKU du parent
            # Nettoyer le nom du parent pour retirer la couleur
            parent["Name"] = nettoyer_nom_produit(parent["Name"], detecter_toutes_couleurs(parent["Name"])).strip()
            parent["Type"] = "variable"
            parent["Attribute 1 name"] = "Couleur"
            parent["Attribute 1 value(s)"] = normaliser_liste_couleurs(couleurs_group_list)
            parent["Attribute 1 visible"] = "yes"
            parent["Attribute 1 global"] = "yes"
            # Vider le Code EAN pour le parent
            parent["Code EAN"] = ""
            parent["Parent SKU"] = ""
            liste_resultats.append(parent)
            
            # Créer une variation pour chaque produit du groupe (y compris le premier)
            for row in rows:
                variation = row.copy()
                variation["Type"] = "variation"
                variation["Parent SKU"] = parent["SKU"]
                var_couleurs = detecter_toutes_couleurs(str(variation["Name"]))
                variation["Attribute 1 name"] = "Couleur"
                variation["Attribute 1 value(s)"] = normaliser_liste_couleurs(var_couleurs)
                variation["Attribute 1 visible"] = "yes"
                variation["Attribute 1 global"] = "yes"
                # Si la variation provient du produit utilisé pour le parent (SKU identique à l'original),
                # modifier son SKU pour garantir l'unicité.
                if str(variation["SKU"]) == sku_orig:
                    if var_couleurs:
                        suffix = var_couleurs[0][:2].upper()  # par exemple "GR" pour "gris"
                    else:
                        suffix = "XX"
                    variation["SKU"] = sku_orig + suffix
                liste_resultats.append(variation)
    
    df_final = pd.DataFrame(liste_resultats)
    return df_final



def main():
    root = Tk()
    root.withdraw()
    
    # 📂 Sélection du fichier CSV
    chemin_fichier = filedialog.askopenfilename(
        filetypes=[("CSV Files", "*.csv")],
        title="Sélectionnez le fichier CSV"
    )
    if not chemin_fichier:
        print("❌ Aucun fichier sélectionné. Fermeture du script.")
        return
    
    try:
        # 📂 Chargement du fichier avec encodage UTF-8
        df = pd.read_csv(chemin_fichier, encoding="utf-8-sig", dtype=str)
        print(f"📂 Fichier chargé : {os.path.basename(chemin_fichier)}")

        # 🛠️ Nettoyage des colonnes
        df.columns = df.columns.str.strip()

        # 🚀 Vérification des colonnes
        print("🔍 Colonnes détectées :", df.columns.tolist())

        # 🛠️ Renommer les colonnes pour WooCommerce
        df = renommer_colonnes_pour_woocommerce(df)
        print("✅ Colonnes après renommage :", df.columns.tolist())

        # 🚨 Vérifier si "Name" est bien présent
        if "Name" not in df.columns:
            raise KeyError(f"❌ La colonne 'Name' est absente après transformation ! Colonnes actuelles : {df.columns.tolist()}")

        # 🛠️ Suppression des doublons
        df = supprimer_doublons_colonnes(df)
        print("✅ Colonnes après suppression des doublons :", df.columns.tolist())

        # 🛠️ Ajustement des catégories
        df = ajuster_categories(df)

        # 🖼️ Formatage des images
        df = formatter_images(df)

        # 🚀 Détection des **produits composites**
        df["Composants composites (encodés en JSON)"] = df["Name"].apply(extraire_couleurs_composite)
        df["Type"] = df["Composants composites (encodés en JSON)"].apply(
            lambda x: "composite" if len(x) > 0 else "variable"
        )

        # ✅ Séparer les produits **composites** des **variables**
        df_composites = df[df["Type"] == "composite"]
        df_variables = df[df["Type"] == "variable"]

        print(f"🛠️ Produits composites détectés : {len(df_composites)}")
        print(f"🛠️ Produits variables détectés : {len(df_variables)}")

        # ✅ Détection des produits avec **une seule couleur** pour être variables
        df_variables["Is_Variable"] = df_variables["Name"].apply(determiner_si_variable)

        # ✅ Séparer les **véritables** produits variables
        df_variables_reels = df_variables[df_variables["Is_Variable"]]

        print(f"✅ Produits variables réellement éligibles : {len(df_variables_reels)}")

        # 🛠️ Regroupement des **produits variables** par couleur
        df_variables_regroupes = regrouper_variations_par_couleur(df_variables_reels)
        print(f"✅ Nombre de produits regroupés : {len(df_variables_regroupes)}")

        # 🔗 Fusion des produits **variables regroupés** et **composites**
        df_final = pd.concat([df_composites, df_variables_regroupes], ignore_index=True)

        # 💾 Export du fichier final
        nouveau_chemin = os.path.splitext(chemin_fichier)[0] + "_final.csv"
        df_final.to_csv(nouveau_chemin, index=False, sep=",", encoding="utf-8-sig")
        print(f"✅ Fichier final exporté avec toutes les données : {nouveau_chemin}")

    except Exception as e:
        print(f"❌ Erreur pendant le traitement : {e}")

if __name__ == "__main__":
    main()

