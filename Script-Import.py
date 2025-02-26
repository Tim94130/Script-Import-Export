# Importation des bibliothèques nécessaires
import pandas as pd
from tkinter import Tk, filedialog
import os
import re
from rapidfuzz import process, fuzz
from collections import defaultdict

############################################
# Fonctions de transformation du CSV
############################################??

def renommer_colonnes_pour_woocommerce(df):
    """
    Renomme automatiquement les colonnes du CSV en utilisant les noms exacts attendus par WooCommerce.
    """
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
    """
    Supprime les colonnes en double en gardant celles en anglais.
    """
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
    colonnes_a_supprimer = [fr_col for fr_col, en_col in correspondance_woocommerce.items() 
                            if fr_col in colonnes_presentes and en_col in colonnes_presentes]
    df.drop(columns=colonnes_a_supprimer, inplace=True, errors='ignore')
    return df

def ajuster_categories(df):
    """
    Fusionne les colonnes de catégories en une seule colonne "Categories" séparée par ' > '.
    """
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
    """
    Fusionne les colonnes d'images en une seule colonne "Images" en y ajoutant l'URL de base.
    """
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
    df['Images'] = df[colonnes_existantes].apply(lambda row: ', '.join(
        [base_url + img.strip() for img in row.dropna().astype(str)]
    ), axis=1)
    print("🔍 Vérification des images fusionnées avec URLs complètes :")
    print(df[['SKU', 'Images']].head())
    if df['Images'].isnull().all():
        print("⚠️ Aucune image fusionnée, les colonnes originales ne seront pas supprimées.")
    else:
        print("✅ Fusion des images réussie avec URLs, suppression des colonnes d'origine.")
        df.drop(columns=colonnes_existantes, inplace=True, errors='ignore')
    return df

def formater_produits(df):
    """
    Reformate les produits pour WooCommerce en mappant les colonnes importantes.
    """
    df['Type'] = df.apply(lambda x: 'variable' if pd.notnull(x.get('Option Couleur (en Français)')) else 'simple', axis=1)
    df['Published'] = 1
    df['Is featured?'] = 0
    df['Visibility in catalog'] = 'visible'
    df['Tax status'] = 'taxable'
    df['In stock?'] = 1
    df['Stock'] = df.get('Stock - Quantité', 0).fillna(0)
    df['Regular price'] = df.get('Prix pour le groupe Défaut', '').fillna('')
    df['Sale price'] = ''
    df['SKU'] = df['Référence']
    df['Name'] = df["Nom de l'article (en Français)"]
    df['Short description'] = df['Description courte (en Français)']
    df['Description'] = df['Description (en Français)']
    df['Brands'] = df['Marque']

############################################
# Fonctions de détection de couleurs
############################################

couleurs_base = [
    "white", "black", "brown", "blue", "red", "pink", "green", 
    "grey", "gray", "yellow", "orange", "purple", "violet",
    "beige", "gold", "silver", 
    "cyan", "magenta", "navy", "maroon", "lime", "olive", "teal", "aqua",
    "blanc", "noir", "marron", "brun", "bleu", "rouge", "rose", 
    "vert", "gris", "jaune", "violet", "beige", "doré", "argent", "kaki",
    "turquoise", "fuchsia", "lavande", "ocre", "ivory", "ivoires", "argenté"
]

adjectifs_ignores = [
    "dark", "light", "pale", "deep", "bright", "medium",
    "fonce", "foncé", "clair", "pâle", "flashy", "fluorescent"
]

mapping_couleurs = {
    "white": "Blanc",
    "black": "Noir",
    "brown": "Marron",
    "blue": "Bleu",
    "aqua": "Bleu",         # Aqua traité comme Bleu
    "red": "Rouge",
    "pink": "Rose",
    "green": "Vert",
    "grey": "Gris",
    "gray": "Gris",
    "yellow": "Jaune",
    "orange": "Orange",
    "purple": "Violet",
    "violet": "Violet",
    "beige": "Beige",
    "taupe": "Beige",       # Taupe traité comme Beige
    "gold": "Doré",
    "silver": "Argent",
    "blanc": "Blanc",
    "noir": "Noir",
    "marron": "Marron",
    "brun": "Marron",
    "bleu": "Bleu",
    "rouge": "Rouge",
    "rose": "Rose",
    "vert": "Vert",
    "gris": "Gris",
    "jaune": "Jaune",
    "doré": "Doré",
    "argent": "Argent",
    "kaki": "Kaki",
    "fushia": "Fuchsia",
    "whiteoff": "Blanc cassé",
}

def detecter_toutes_couleurs(nom_produit: str):
    """
    Retourne la liste de toutes les couleurs détectées dans le nom du produit,
    en ignorant les adjectifs (ex. dark, light, etc.).
    """
    if not isinstance(nom_produit, str):
        return []
    tokens = re.split(r"[\s\-\|\(\),/]+", nom_produit.lower())
    print(f"Produit : {nom_produit}")
    print(f"Tokens  : {tokens}")
    trouvees = []
    for t in tokens:
        if t in adjectifs_ignores:
            continue
        if t in couleurs_base and t not in trouvees:
            trouvees.append(t)
    return trouvees

def normaliser_liste_couleurs(couleurs_brutes: list):
    """
    Convertit chaque couleur brute en version FR normalisée via mapping_couleurs.
    Retourne une chaîne, ex: "Marron, Vert".
    """
    if not couleurs_brutes:
        return ""
    resultat = []
    for c in couleurs_brutes:
        c_lower = c.lower()
        resultat.append(mapping_couleurs.get(c_lower, "Non spécifiée"))
    resultat = list(dict.fromkeys(resultat))
    return ", ".join(resultat)

def nom_sans_couleur(nom_produit: str) -> str:
    """
    Renvoie le "nom de base" en retirant la dernière partie après un tiret (basique).
    """
    parts = nom_produit.split("-")
    if len(parts) > 1:
        return "-".join(parts[:-1]).strip()
    else:
        return nom_produit.strip()

############################################
# Fonction pour créer produits groupés et variables
############################################

def creer_produits_grouped_et_variables_par_couleur(df):
    """
    Transforme df en un DataFrame adapté à WooCommerce en créant :
      - Pour les produits dont le "Nom Base" contient "pack" (insensible à la casse) :
          * Un produit parent de type "grouped".
          * Pour chaque ligne du groupe, un produit enfant de type "simple" avec Parent = SKU du parent.
      - Pour les autres produits (non "pack") :
          * S'il n'y a qu'une seule ligne pour un même "Nom Base", le produit reste "simple".
          * S'il y a plusieurs lignes, on crée :
              - Une ligne parent (Type = "variable") qui agrège toutes les couleurs uniques détectées dans "Couleurs Normalisées".
              - Une ligne variation par couleur unique (Type = "variation") avec Parent = SKU du parent.
              - Pour chaque variation, on affecte la galerie d’images propre à la couleur (ou celle du parent en fallback).
              - Le titre de la variation est reconstruit à partir du "Nom Base" et de la couleur.
              - La colonne "Code EAN" est vidée pour les variations.
              
      De plus, le produit parent se voit attribuer un attribut par défaut ("Default attribute 1") afin que la couleur
      par défaut soit pré-sélectionnée sur la fiche produit.
    """
    from collections import defaultdict

    rows = []
    # Extraction du "Nom Base" sans la partie couleur
    df["Nom Base"] = df["Name"].apply(nom_sans_couleur)
    groupes = df.groupby("Nom Base", dropna=False)
    
    for base_name, group in groupes:
        print(f"\n>>> Traitement du groupe : '{base_name}' avec {len(group)} ligne(s)")
        
        # CAS 1 : Nom Base contenant "pack" => produit groupé
        if "pack" in base_name.lower():
            parent = group.iloc[0].copy()
            sku_parent = str(parent.get("SKU", ""))
            parent["Type"] = "grouped"
            parent["Parent"] = ""
            parent["Attribute 1 name"] = ""
            parent["Attribute 1 value(s)"] = ""
            parent["Attribute 1 visible"] = ""
            parent["Attribute 1 variation"] = ""
            parent["Attribute 1 global"] = ""
            parent["Variations"] = ""
            rows.append(parent)
            print(f"  -> Produit groupé créé (SKU: {sku_parent})")

            for _, row_src in group.iterrows():
                enfant = row_src.copy()
                enfant["Type"] = "simple"
                enfant["Parent"] = sku_parent
                rows.append(enfant)
                print(f"     -> Enfant groupé ajouté (SKU: {enfant.get('SKU', '')})")

        # CAS 2 : Nom Base unique => produit simple
        elif len(group) == 1:
            simple = group.iloc[0].copy()
            simple["Type"] = "simple"
            simple["Parent"] = ""
            simple["Variations"] = ""
            rows.append(simple)
            print(f"  -> Produit simple (SKU: {simple.get('SKU', '')})")

        # CAS 3 : Nom Base commun à plusieurs lignes => produit variable
        else:
            parent = group.iloc[0].copy()
            sku_parent = str(parent.get("SKU", ""))
            set_couleurs = set()
            color_to_images = defaultdict(list)
            
            # Récupération des couleurs et des images associées pour chaque ligne
            for _, row_src in group.iterrows():
                c_str = row_src.get("Couleurs Normalisées", "")
                row_images = row_src.get("Images", "")
                print(f"[DEBUG] Ligne SKU='{row_src.get('SKU','')}' => Couleurs Normalisées: '{c_str}'")
                print(f"[DEBUG] Ligne SKU='{row_src.get('SKU','')}' => Images: '{row_images}'")

                if c_str:
                    couleurs_de_ligne = [couleur.strip() for couleur in c_str.split(",") if couleur.strip()]
                    for coul in couleurs_de_ligne:
                        set_couleurs.add(coul)
                        if isinstance(row_images, str) and row_images.strip():
                            color_to_images[coul].append(row_images)
            
            # Si aucune couleur n'est détectée, on traite tout le groupe comme simple
            if not set_couleurs:
                print(f"⚠️ Aucune couleur détectée pour '{base_name}', traité comme produit simple.")
                for _, row_src in group.iterrows():
                    simple = row_src.copy()
                    simple["Type"] = "simple"
                    simple["Parent"] = ""
                    simple["Variations"] = ""
                    rows.append(simple)
            else:
                # Création du produit parent variable
                parent["Type"] = "variable"
                parent["Parent"] = ""
                parent["Attribute 1 name"] = "Couleur"
                parent["Attribute 1 value(s)"] = ", ".join(sorted(set_couleurs))
                parent["Attribute 1 visible"] = "yes"
                parent["Attribute 1 variation"] = "yes"
                parent["Attribute 1 global"] = "yes"
                parent["Variations"] = ", ".join(sorted(set_couleurs))

                # Définir la couleur par défaut
                default_color = None
                for coul in sorted(set_couleurs):
                    if coul.lower() in parent["Name"].lower():
                        default_color = coul
                        break
                if default_color is None:
                    default_color = sorted(set_couleurs)[0]
                parent["Default attribute 1"] = default_color

                rows.append(parent)
                print(f"  -> Produit parent variable créé (SKU: {sku_parent}) avec couleurs : {', '.join(sorted(set_couleurs))}")
                print(f"     Couleur par défaut définie : {default_color}")

                # Galerie d'images par défaut du parent
                images_parent = ""
                if "Images" in parent and parent["Images"]:
                    images_parent = parent["Images"].strip()
                    print(f"     -> Galerie du parent (SKU: {sku_parent}): {images_parent}")
                else:
                    print(f"     -> Aucune image définie pour le parent (SKU: {sku_parent}).")

                # Création des variations par couleur
                for coul in sorted(set_couleurs):
                    variation = parent.copy()
                    variation["SKU"] = f"{sku_parent}-{coul.lower()}"
                    variation["Type"] = "variation"
                    variation["Parent"] = sku_parent
                    variation["Attribute 1 name"] = "Couleur"
                    variation["Attribute 1 value(s)"] = coul
                    variation["Attribute 1 visible"] = "yes"
                    variation["Attribute 1 variation"] = "yes"
                    variation["Attribute 1 global"] = "yes"
                    variation["Variations"] = ""
                    variation["Description"] = ""
                    variation["Short description"] = ""

                    # Reconstruction du titre
                    if "Nom Base" in variation:
                        variation["Name"] = f"{variation['Nom Base']} - {coul}"
                    else:
                        variation["Name"] = f"{parent['Name']} - {coul}"

                    # Affectation des images spécifiques à la couleur
                    liste_images_couleur = []
                    if coul in color_to_images:
                        for bloc_img in color_to_images[coul]:
                            for url_img in bloc_img.split(","):
                                url_img = url_img.strip()
                                if url_img:
                                    liste_images_couleur.append(url_img)
                                    print(f"[DEBUG] Couleur '{coul}' => url_img = {url_img}")
                    
                    # Log de la liste avant fallback
                    print(f"[DEBUG] Couleur '{coul}' => liste_images_couleur = {liste_images_couleur}")
                    
                    # Suppression des doublons en conservant l'ordre
                    liste_images_couleur = list(dict.fromkeys(liste_images_couleur))

                    if len(liste_images_couleur) == 0:
                        variation["Images"] = images_parent
                        print(f"[DEBUG] Couleur '{coul}' => Aucune image, fallback sur le parent: {images_parent}")
                    else:
                        variation["Images"] = ", ".join(liste_images_couleur)
                        print(f"[DEBUG] Couleur '{coul}' => Images variation: {variation['Images']}")

                    # Vidage de "Code EAN" pour éviter les duplications
                    if "Code EAN" in variation:
                        variation["Code EAN"] = ""

                    rows.append(variation)
                    print(f"  -> Variation créée pour '{base_name}' : Couleur = {coul}, SKU = {variation['SKU']}, Name = {variation['Name']}")
                    print(f"     Images de la variation : {variation['Images']}")

    df_res = pd.DataFrame(rows)
    return df_res



############################################
# Fonction principale
############################################

def main():
    """
    Gère l'exécution principale du script.
    Permet de sélectionner un fichier CSV, le traiter et sauvegarder un fichier final
    qui contient toutes les modifications (renommage, formatage, détection des couleurs),
    la suppression des colonnes en double, ET la structure produit variable ou groupé.
    """
    root = Tk()
    root.withdraw()
    
    chemin_fichier = filedialog.askopenfilename(
        filetypes=[("CSV Files", "*.csv")],
        title="Sélectionnez le fichier CSV"
    )
    if not chemin_fichier:
        print("Aucun fichier sélectionné. Fermeture du script.")
        return

    try:
        df = pd.read_csv(chemin_fichier)
        print(f"📂 Fichier chargé avec succès : {os.path.basename(chemin_fichier)}")
        
        # 1. Renommer les colonnes pour WooCommerce
        df_modifie = renommer_colonnes_pour_woocommerce(df)
        print("✅ Colonnes renommées pour WooCommerce.")
        
        # 2. Supprimer les colonnes en double
        df_modifie = supprimer_doublons_colonnes(df_modifie)
        print("✅ Colonnes en double supprimées (si présentes).")
        
        # 3. Ajuster les catégories
        df_modifie = ajuster_categories(df_modifie)
        print("✅ Catégories ajustées.")
        
        # 4. Formater les images
        df_modifie = formatter_images(df_modifie)
        print("✅ Images formatées.")
        
        # 5. Détection des couleurs basée sur "Name"
        if "Name" in df_modifie.columns:
            df_modifie["Liste Couleurs Brutes"] = df_modifie["Name"].apply(detecter_toutes_couleurs)
            df_modifie["Couleurs Normalisées"] = df_modifie["Liste Couleurs Brutes"].apply(normaliser_liste_couleurs)
            df_modifie["Attribute 1 name"] = "Couleur"
            df_modifie["Attribute 1 value(s)"] = df_modifie["Couleurs Normalisées"]
            df_modifie["Attribute 1 visible"] = 1
            df_modifie["Attribute 1 global"] = 1
            print("✅ Couleurs détectées et colonnes d'attributs remplies.")
        else:
            print("⚠️ La colonne 'Name' n'existe pas, impossible de détecter la couleur !")
        
        # 6. Création du DataFrame final avec structure produit variable ou groupé
        df_final = creer_produits_grouped_et_variables_par_couleur(df_modifie)
        print("✅ Structure produit (variables/groupés) créée.")
        
        # 7. Export du CSV final complet
        nouveau_chemin = os.path.splitext(chemin_fichier)[0] + "_final.csv"
        df_final.to_csv(nouveau_chemin, index=False, sep=",", encoding="utf-8-sig")
        print(f"✅ Fichier final exporté avec succès : {nouveau_chemin}")
    
    except Exception as e:
        print(f"❌ Une erreur est survenue : {e}")

if __name__ == "__main__":
    main()
