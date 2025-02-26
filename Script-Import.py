# Importation des bibliothèques nécessaires
import pandas as pd
from tkinter import Tk, filedialog
import os
import re
from collections import defaultdict
from rapidfuzz import process, fuzz  # Si nécessaire

# Définitions globales pour la détection des couleurs
adjectifs_ignores = [
    "dark", "light", "pale", "deep", "bright", "medium",
    "fonce", "foncé", "clair", "pâle", "flashy", "fluorescent"
]

couleurs_base = [
    "white", "black", "brown", "blue", "red", "pink", "green", 
    "grey", "gray", "yellow", "orange", "purple", "violet",
    "beige", "gold", "silver", 
    "cyan", "magenta", "navy", "maroon", "lime", "olive", "teal", "aqua",
    "blanc", "noir", "marron", "brun", "bleu", "rouge", "rose", 
    "vert", "gris", "jaune", "violet", "beige", "doré", "argent", "kaki",
    "turquoise", "fuchsia", "lavande", "ocre", "ivory", "ivoires", "argenté"
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
    colonnes_a_supprimer = [fr_col for fr_col, en_col in correspondance_woocommerce.items() 
                            if fr_col in colonnes_presentes and en_col in colonnes_presentes]
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
    df['Images'] = df[colonnes_existantes].apply(lambda row: ", ".join([base_url + img.strip() for img in row.dropna().astype(str)]), axis=1)
    print("🔍 Vérification des images fusionnées avec URLs complètes :")
    print(df[['SKU', 'Images']].head())
    if df['Images'].isnull().all():
        print("⚠️ Aucune image fusionnée, les colonnes originales ne seront pas supprimées.")
    else:
        print("✅ Fusion des images réussie avec URLs, suppression des colonnes d'origine.")
        df.drop(columns=colonnes_existantes, inplace=True, errors='ignore')
    return df

def formater_produits(df):
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
    return df

############################################
# Fonctions de détection/extraction des couleurs
############################################
def detecter_toutes_couleurs(nom_produit: str):
    if not isinstance(nom_produit, str):
        return []
    tokens = re.split(r"[\s\-\|\(\),/]+", nom_produit.lower())
    print(f"[detecter_toutes_couleurs] Produit : {nom_produit}")
    print(f"[detecter_toutes_couleurs] Tokens  : {tokens}")
    trouvees = []
    for t in tokens:
        if t in adjectifs_ignores:
            continue
        if t in couleurs_base:
            trouvees.append(t)
    if trouvees:
        derniere_couleur_brute = trouvees[-1]
        print(f"[detecter_toutes_couleurs] Dernière couleur détectée (brute) : {derniere_couleur_brute}")
        derniere_couleur_fr = mapping_couleurs.get(derniere_couleur_brute.lower(), derniere_couleur_brute).title()
        print(f"[detecter_toutes_couleurs] Dernière couleur détectée (FR) : {derniere_couleur_fr}")
        return [derniere_couleur_fr]
    else:
        print(f"[detecter_toutes_couleurs] Aucune couleur détectée.")
        return []

def nom_sans_couleur(nom_produit: str) -> str:
    parts = nom_produit.split("-")
    if len(parts) > 1:
        result = "-".join(parts[:-1]).strip()
    else:
        result = nom_produit.strip()
    print(f"[nom_sans_couleur] '{nom_produit}' -> '{result}'")
    return result
def normaliser_liste_couleurs(couleurs_brutes: list):
    if not couleurs_brutes:
        return ""
    resultat = []
    for c in couleurs_brutes:
        c_lower = c.lower()
        resultat.append(mapping_couleurs.get(c_lower, "Non spécifiée"))
    resultat = list(dict.fromkeys(resultat))
    return ", ".join(resultat)
def extraire_siege_chassis_parentheses(nom_produit: str) -> (str, str):
    """
    Extrait la couleur du siège (avant la parenthèse) et la couleur du châssis (dans la parenthèse),
    ex: "Peach Pink (Rosegold Frame)" -> ("Peach Pink", "Rosegold")
    """
    pattern = r"(.*?)\s*\((.*?)\)"
    match = re.search(pattern, nom_produit)
    if match:
        # Partie avant la parenthèse : siège
        seat_raw = match.group(1).strip()
        # Partie entre parenthèses : châssis
        chassis_raw = match.group(2).strip()
        # Optionnel : retirer "Frame" ou autre mot superflu
        chassis_raw = chassis_raw.replace("Frame", "").strip()
        
        # Appliquer un mapping/correction
        seat_lower = seat_raw.lower()
        chassis_lower = chassis_raw.lower()
        seat_fr = mapping_couleurs.get(seat_lower, seat_lower).title()
        chassis_fr = mapping_couleurs.get(chassis_lower, chassis_lower).title()
        
        print(f"[extraire_siege_chassis_parentheses] '{nom_produit}' -> Siège: '{seat_fr}', Châssis: '{chassis_fr}'")
        return seat_fr, chassis_fr
    else:
        # Si le titre ne correspond pas au format "XYZ (ABC)", on renvoie des valeurs vides
        return ("", "")

############################################
# Fonction pour créer produits groupés et variables
############################################

def creer_produits_grouped_et_variables_par_couleur(df):
    """
    Crée un DataFrame final pour WooCommerce.
    Si le titre correspond au format "Siège (Châssis Frame)", ex: "Peach Pink (Rosegold Frame)",
    on extrait les deux couleurs distinctes. Sinon, fallback sur la logique existante.
    """
    rows = []
    df["Nom Base"] = df["Name"].apply(nom_sans_couleur)
    groupes = df.groupby("Nom Base", dropna=False)
    
    for base_name, group in groupes:
        print(f"\n>>> Traitement du groupe : '{base_name}' avec {len(group)} ligne(s)")
        
        # Vérifions si le premier produit du groupe correspond à un titre du type "XYZ (ABC)"
        seat_color, chassis_color = extraire_siege_chassis_parentheses(group.iloc[0]["Name"])
        
        if seat_color and chassis_color:
            # On a détecté un format "Siège (Châssis Frame)"
            print(f"[INFO] Produit format 'Siège (Châssis)' détecté : {base_name}")
            group = group.copy()
            group["Seat Color"] = seat_color
            group["Chassis Color"] = chassis_color
            
            # Créons un parent variable à deux attributs : "Siège" et "Châssis"
            if len(group) == 1:
                # Si on n'a qu'une seule ligne, c'est un simple
                simple = group.iloc[0].copy()
                simple["Type"] = "simple"
                simple["Parent"] = ""
                rows.append(simple)
                print(f"  -> Produit simple (SKU: {simple.get('SKU', '')})")
            else:
                # Parent
                parent = group.iloc[0].copy()
                sku_parent = str(parent.get("SKU", ""))
                parent["Type"] = "variable"
                parent["Parent"] = ""
                # On mappe "Siège" sur l'attribut 1, "Châssis" sur l'attribut 2 (ou l'inverse)
                parent["Attribute 1 name"] = "Siège"
                parent["Attribute 2 name"] = "Châssis"
                parent["Attribute 1 value(s)"] = seat_color
                parent["Attribute 2 value(s)"] = chassis_color
                parent["Attribute 1 visible"] = "yes"
                parent["Attribute 2 visible"] = "yes"
                parent["Attribute 1 variation"] = "yes"
                parent["Attribute 2 variation"] = "yes"
                parent["Name"] = base_name
                parent["Default attribute 1"] = seat_color
                parent["Default attribute 2"] = chassis_color
                rows.append(parent)
                print(f"  -> Produit parent variable créé (SKU: {sku_parent}) avec Siège: {seat_color}, Châssis: {chassis_color}")
                
                # Variation 1 : siège
                variation_seat = parent.copy()
                variation_seat["SKU"] = f"{sku_parent}-{seat_color.lower().replace(' ','-')}"
                variation_seat["Type"] = "variation"
                variation_seat["Parent"] = sku_parent
                variation_seat["Name"] = f"{base_name} - Siège {seat_color}"
                rows.append(variation_seat)
                print(f"     -> Variation créée pour le siège : {variation_seat['SKU']} - {variation_seat['Name']}")
                
                # Variation 2 : châssis
                variation_chassis = parent.copy()
                variation_chassis["SKU"] = f"{sku_parent}-{chassis_color.lower().replace(' ','-')}"
                variation_chassis["Type"] = "variation"
                variation_chassis["Parent"] = sku_parent
                variation_chassis["Name"] = f"{base_name} - Châssis {chassis_color}"
                rows.append(variation_chassis)
                print(f"     -> Variation créée pour le châssis : {variation_chassis['SKU']} - {variation_chassis['Name']}")
                
        else:
            # Sinon, on applique la logique classique (une seule couleur ou pas de parenthèses)
            if len(group) == 1:
                simple = group.iloc[0].copy()
                simple["Type"] = "simple"
                simple["Parent"] = ""
                simple["Variations"] = ""
                rows.append(simple)
                print(f"  -> Produit simple (SKU: {simple.get('SKU', '')})")
            else:
                parent = group.iloc[0].copy()
                sku_parent = str(parent.get("SKU", ""))
                set_couleurs = set()
                color_to_images = defaultdict(list)
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
                if not set_couleurs:
                    print(f"⚠️ Aucune couleur détectée pour '{base_name}', traité comme produit simple.")
                    for _, row_src in group.iterrows():
                        simple = row_src.copy()
                        simple["Type"] = "simple"
                        simple["Parent"] = ""
                        simple["Variations"] = ""
                        rows.append(simple)
                else:
                    parent["Type"] = "variable"
                    parent["Parent"] = ""
                    parent["Attribute 1 name"] = "Couleur"
                    parent["Attribute 1 value(s)"] = ", ".join(sorted(set_couleurs))
                    parent["Attribute 1 visible"] = "yes"
                    parent["Attribute 1 variation"] = "yes"
                    parent["Attribute 1 global"] = "yes"
                    parent["Variations"] = ", ".join(sorted(set_couleurs))
                    parent["Name"] = base_name
                    default_color = sorted(set_couleurs)[0]
                    parent["Default attribute 1"] = default_color
                    rows.append(parent)
                    print(f"  -> Produit parent variable créé (SKU: {sku_parent}) avec couleurs : {', '.join(sorted(set_couleurs))}")
                    print(f"     Couleur par défaut définie : {default_color}")
                    
                    images_parent = parent.get("Images", "").strip() if parent.get("Images", "") else ""
                    if images_parent:
                        print(f"     -> Galerie du parent (SKU: {sku_parent}): {images_parent}")
                    else:
                        print(f"     -> Aucune image définie pour le parent (SKU: {sku_parent}).")
                    
                    for coul in sorted(set_couleurs):
                        variation = parent.copy()
                        variation["SKU"] = f"{sku_parent}-{coul.lower().replace(' ','-')}"
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
                        if "Nom Base" in variation:
                            variation["Name"] = f"{variation['Nom Base']} - {coul}"
                        else:
                            variation["Name"] = f"{parent['Name']} - {coul}"
                        
                        liste_images_couleur = []
                        if coul in color_to_images:
                            for bloc_img in color_to_images[coul]:
                                for url_img in bloc_img.split(","):
                                    url_img = url_img.strip()
                                    if url_img:
                                        liste_images_couleur.append(url_img)
                                        print(f"[DEBUG] Couleur '{coul}' => url_img: {url_img}")
                        print(f"[DEBUG] Couleur '{coul}' => liste_images_couleur avant suppression doublons: {liste_images_couleur}")
                        liste_images_couleur = list(dict.fromkeys(liste_images_couleur))
                        print(f"[DEBUG] Couleur '{coul}' => liste_images_couleur après suppression doublons: {liste_images_couleur}")
                        
                        if len(liste_images_couleur) == 0:
                            variation["Images"] = images_parent
                            print(f"[DEBUG] Couleur '{coul}' => Aucune image spécifique trouvée, fallback sur parent: {images_parent}")
                        else:
                            variation["Images"] = ", ".join(liste_images_couleur)
                            print(f"[DEBUG] Couleur '{coul}' => Images variation: {variation['Images']}")
                        
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
        
        # Étapes de transformation
        df_modifie = renommer_colonnes_pour_woocommerce(df)
        df_modifie = supprimer_doublons_colonnes(df_modifie)
        df_modifie = ajuster_categories(df_modifie)
        df_modifie = formatter_images(df_modifie)
        
        # Optionnel : formater_produits si nécessaire
        # df_modifie = formater_produits(df_modifie)
        
        if "Name" in df_modifie.columns:
            df_modifie["Liste Couleurs Brutes"] = df_modifie["Name"].apply(detecter_toutes_couleurs)
            # Détection classique de la dernière couleur, stockée dans Couleurs Normalisées
            df_modifie["Liste Couleurs Brutes"] = df_modifie["Name"].apply(detecter_toutes_couleurs)
            df_modifie["Couleurs Normalisées"] = df_modifie["Liste Couleurs Brutes"].apply(normaliser_liste_couleurs)
            df_modifie["Attribute 1 name"] = "Couleur"
            df_modifie["Attribute 1 value(s)"] = df_modifie["Couleurs Normalisées"]
            df_modifie["Attribute 1 visible"] = 1
            df_modifie["Attribute 1 global"] = 1
            print("✅ Couleurs détectées et colonnes d'attributs remplies.")
        else:
            print("⚠️ La colonne 'Name' n'existe pas, impossible de détecter la couleur !")
        
        # Création du DataFrame final
        df_final = creer_produits_grouped_et_variables_par_couleur(df_modifie)
        print("✅ Structure produit (variables/groupés) créée.")
        
        # Export
        nouveau_chemin = os.path.splitext(chemin_fichier)[0] + "_final.csv"
        df_final.to_csv(nouveau_chemin, index=False, sep=",", encoding="utf-8-sig")
        print(f"✅ Fichier final exporté avec succès : {nouveau_chemin}")
    
    except Exception as e:
        print(f"❌ Une erreur est survenue : {e}")

if __name__ == "__main__":
    main()
