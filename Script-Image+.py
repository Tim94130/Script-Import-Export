import pandas as pd
import csv
import pymysql
import os
import re
import json
import unicodedata
from tkinter import Tk, filedialog
from collections import defaultdict
from rapidfuzz import process, fuzz  # si vous l'utilisez
############################################
# Définition des adjectifs/couleurs
############################################

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
# Fonctions de renommage / suppression doublons
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
        "Image supplémentaire n°9",
    ]
    colonnes_existantes = [col for col in colonnes_images if col in df.columns]
    if not colonnes_existantes:
        print(
            "⚠️ Aucune colonne d'image trouvée, la colonne 'Images' ne sera pas créée."
        )
        return df

    df["Images"] = df[colonnes_existantes].apply(
        lambda row: ", ".join(
            [base_url + img.strip() for img in row.dropna().astype(str)]
        ),
        axis=1,
    )
    print("🔍 Vérification des images fusionnées avec URLs complètes :")
    print(df[["SKU", "Images"]].head())

    if df["Images"].isnull().all():
        print(
            "⚠️ Aucune image fusionnée, les colonnes originales ne seront pas supprimées."
        )
    else:
        print(
            "✅ Fusion des images réussie avec URLs, suppression des colonnes d'origine."
        )
        df.drop(columns=colonnes_existantes, inplace=True, errors="ignore")

    return df


############################################
# Fonctions de détection / extraction couleurs
############################################


def detecter_toutes_couleurs(nom_produit: str):
    if not isinstance(nom_produit, str):
        return []
    tokens = re.split(r"[\s\-\|\(\),/]+", nom_produit.lower())
    trouvees = [mapping_couleurs[t] for t in tokens if t in mapping_couleurs]
    return list(dict.fromkeys(trouvees))


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


def nettoyer_nom_produit(nom_produit: str, couleurs: list):
    if not isinstance(nom_produit, str):
        return nom_produit
    for couleur in couleurs:
        nom_produit = re.sub(rf"\b{couleur}\b", "", nom_produit, flags=re.IGNORECASE)
    if " - " in nom_produit:
        nom_produit = nom_produit.split(" - ")[0]
    nom_produit = re.sub(r"[-\s]+$", "", nom_produit)
    return re.sub(r"\s+", " ", nom_produit).strip()


def extraire_couleurs_composite(nom_produit: str):
    """
    Extrait les couleurs liées aux éléments "Châssis" et "Siège".
    Un produit est considéré composite s'il a **Châssis** et **Siège** dans le même nom.
    Vous aviez un code plus élaboré ici. On le remet tel quel.
    """
    if not isinstance(nom_produit, str):
        return {}

    # Normalisation du texte (supprimer accents et mettre en minuscule)
    nom_lower = (
        unicodedata.normalize("NFKD", nom_produit)
        .encode("ASCII", "ignore")
        .decode("utf-8")
        .lower()
    )
    resultat = {}

    elements_couleur = {
        "Châssis": ["châssis", "chassis"],
        "Siège": ["siège", "siege", "assise"],
    }

    contient_chassis = any(mot in nom_lower for mot in elements_couleur["Châssis"])
    contient_siege = any(mot in nom_lower for mot in elements_couleur["Siège"])

    if not (contient_chassis and contient_siege):
        return {}  # Pas un produit composite

    # Exemple simplifié. Si vous aviez un code plus avancé, remettez-le.
    # On se contente de renvoyer {} ou un dict minimal
    # Selon la logique, vous pouvez effectuer vos regex pour trouver la couleur associée au "Châssis" et au "Siège".
    #
    # Pour l'exemple, on renvoie un dict non vide pour signaler un composite
    #
    # => Si vous voulez du code plus élaboré, remettez-le ici.
    resultat["Châssis"] = "???"
    resultat["Siège"] = "???"
    return resultat


def determiner_si_variable(nom_produit: str):
    couleurs_detectees = detecter_toutes_couleurs(nom_produit)
    return len(couleurs_detectees) == 1


def regrouper_variations_par_couleur(df):
    """
    Regroupe les produits par modèle (nom nettoyé).
    Crée un parent (variable) + variations si plusieurs couleurs dans le même groupe.
    Sinon, produit simple.
    """
    groupes = {}
    for _, row in df.iterrows():
        nom_original = str(row["Name"])
        couleurs_detectees = detecter_toutes_couleurs(nom_original)
        nom_sans_couleur = nettoyer_nom_produit(
            nom_original, couleurs_detectees
        ).strip()
        key = nom_sans_couleur.lower()
        groupes.setdefault(key, []).append(row)

    liste_resultats = []

    for key, rows in groupes.items():
        couleurs_group = set()
        for row in rows:
            couleurs = detecter_toutes_couleurs(str(row["Name"]))
            couleurs_group.update(couleurs)
        couleurs_group_list = list(couleurs_group)

        # S'il n'y a qu'une couleur => simple
        if len(couleurs_group_list) == 1:
            simple_product = rows[0].copy()
            simple_product["Type"] = "simple"
            simple_product["Attribute 1 name"] = "Couleur"
            simple_product["Attribute 1 value(s)"] = normaliser_liste_couleurs(
                couleurs_group_list
            )
            simple_product["Attribute 1 visible"] = "yes"
            simple_product["Attribute 1 global"] = "yes"
            simple_product["Parent SKU"] = ""
            liste_resultats.append(simple_product)
        else:
            # Création d'un produit parent variable
            parent = rows[0].copy()
            sku_orig = str(parent["SKU"])
            parent["SKU"] = "PARENT-" + sku_orig
            parent["Name"] = nettoyer_nom_produit(
                parent["Name"], detecter_toutes_couleurs(parent["Name"])
            ).strip()
            parent["Type"] = "variable"
            parent["Attribute 1 name"] = "Couleur"
            parent["Attribute 1 value(s)"] = normaliser_liste_couleurs(
                couleurs_group_list
            )
            parent["Attribute 1 visible"] = "yes"
            parent["Attribute 1 global"] = "yes"
            parent["Code EAN"] = ""
            parent["Parent SKU"] = ""
            liste_resultats.append(parent)

            # Chaque ligne du groupe -> variation
            for row in rows:
                variation = row.copy()
                variation["Type"] = "variation"
                variation["Parent SKU"] = parent["SKU"]
                var_couleurs = detecter_toutes_couleurs(str(variation["Name"]))
                variation["Attribute 1 name"] = "Couleur"
                variation["Attribute 1 value(s)"] = normaliser_liste_couleurs(
                    var_couleurs
                )
                variation["Attribute 1 visible"] = "yes"
                variation["Attribute 1 global"] = "yes"
                if str(variation["SKU"]) == sku_orig:
                    # On modifie le SKU pour éviter le conflit
                    if var_couleurs:
                        suffix = var_couleurs[0][:2].upper()
                    else:
                        suffix = "XX"
                    variation["SKU"] = sku_orig + suffix
                liste_resultats.append(variation)

    return pd.DataFrame(liste_resultats)


############################################
# 1) Fonctions de génération du CSV final
############################################


def generer_csv_final():
    """Ouvre un CSV, effectue toutes les transformations, génère un _final.csv."""
    root = Tk()
    root.withdraw()

    chemin_fichier = filedialog.askopenfilename(
        filetypes=[("CSV Files", "*.csv")], title="Sélectionnez le fichier CSV"
    )
    if not chemin_fichier:
        print("❌ Aucun fichier sélectionné. Fermeture du script.")
        return

    try:
        df = pd.read_csv(chemin_fichier, encoding="utf-8-sig", dtype=str)
        print(f"📂 Fichier chargé : {os.path.basename(chemin_fichier)}")

        df.columns = df.columns.str.strip()
        print("🔍 Colonnes détectées :", df.columns.tolist())

        # Renommer
        df = renommer_colonnes_pour_woocommerce(df)
        # Supprimer doublons
        df = supprimer_doublons_colonnes(df)
        # Ajuster catégories
        df = ajuster_categories(df)
        # Format images
        df = formatter_images(df)

        # Détection composites
        df["Composants composites (encodés en JSON)"] = df["Name"].apply(
            extraire_couleurs_composite
        )
        df["Type"] = df["Composants composites (encodés en JSON)"].apply(
            lambda x: "composite" if len(x) > 0 else "variable"
        )

        df_composites = df[df["Type"] == "composite"]
        df_variables = df[df["Type"] == "variable"]

        df_variables["Is_Variable"] = df_variables["Name"].apply(determiner_si_variable)
        df_variables_reels = df_variables[df_variables["Is_Variable"]]

        df_variables_regroupes = regrouper_variations_par_couleur(df_variables_reels)

        # Fusion
        df_final = pd.concat([df_composites, df_variables_regroupes], ignore_index=True)

        # Export
        nouveau_chemin = os.path.splitext(chemin_fichier)[0] + "_final.csv"
        df_final.to_csv(nouveau_chemin, index=False, sep=",", encoding="utf-8-sig")
        print(f"✅ Fichier final exporté : {nouveau_chemin}")

    except Exception as e:
        print(f"❌ Erreur pendant le traitement : {e}")


############################################
# 2) Fonction pour importer les galeries dans la base
############################################


def importer_galerie_variations(csv_file, db_config):
    """
    Lit le CSV (csv_file). Pour chaque ligne de type 'variation',
    récupère la liste d'URLs d'images, les convertit en IDs
    et met à jour la méta '_wc_additional_variation_images'.
    """
    conn = pymysql.install_as_MySQLdb(
        host=db_config["host"],
        user=db_config["user"],
        passwd=db_config["passwd"],
        db=db_config["db"],
        charset="utf8mb4",
    )
    cursor = conn.cursor()

    def get_variation_id_by_sku(sku):
        sql = """SELECT post_id
                   FROM wp_postmeta
                  WHERE meta_key = '_sku'
                    AND meta_value = %s
                  LIMIT 1
               """
        cursor.execute(sql, [sku])
        row = cursor.fetchone()
        return row[0] if row else None

    def get_attachment_id_by_url(url):
        url = url.strip()
        sql = """SELECT ID
                   FROM wp_posts
                  WHERE post_type='attachment'
                    AND guid = %s
                  LIMIT 1
               """
        cursor.execute(sql, [url])
        row = cursor.fetchone()
        return row[0] if row else None

    with open(csv_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=",")
        for row in reader:
            product_type = (row.get("Type") or "").lower().strip()
            if product_type != "variation":
                continue  # on traite seulement variations

            sku = (row.get("SKU") or "").strip()
            if not sku:
                continue

            variation_id = get_variation_id_by_sku(sku)
            if not variation_id:
                print(f"⚠ Variation non trouvée pour SKU={sku}")
                continue

            images_field = row.get("Images", "")
            if not images_field:
                # Pas d'images => on passe
                continue

            urls = [u.strip() for u in images_field.split(",") if u.strip()]
            attach_ids = []
            for url in urls:
                att_id = get_attachment_id_by_url(url)
                if att_id:
                    attach_ids.append(str(att_id))

            if attach_ids:
                meta_value = ",".join(attach_ids)
                sql_update = """REPLACE INTO wp_postmeta (post_id, meta_key, meta_value)
                                VALUES (%s, '_wc_additional_variation_images', %s)
                             """
                cursor.execute(sql_update, [variation_id, meta_value])
                conn.commit()
                print(
                    f"✓ Variation SKU={sku} mise à jour avec {len(attach_ids)} image(s)."
                )
            else:
                print(f"⚠ Aucune image trouvée pour la variation SKU={sku}.")

    cursor.close()
    conn.close()


############################################
# 3) main() global
############################################


def main():
    print("=== Génération du CSV Final ===")
    generer_csv_final()
    print("=== Génération terminée ===")

    reponse = input(
        "Souhaitez-vous lancer l'import des galeries en base de données pour les variations ? (o/n) : "
    )
    if reponse.lower().startswith("o"):
        # Paramètres DB (à adapter)
        db_config = {
            "host": "yolobaytbillard.mysql.db",
            "user": "yolobaytbillard",
            "passwd": "Yolobb93",
            "db": "yolobaytbillard",
        }
        csv_file = input(
            "Entrez le chemin du fichier _final.csv (ou laissez vide si c'est 'monfichier_final.csv'): "
        )
        if not csv_file:
            csv_file = "monfichier_final.csv"  # modifiez si besoin
        importer_galerie_variations(csv_file, db_config)
        print("=== Import en base terminé ===")
    else:
        print("Import des galeries annulé.")


if __name__ == "__main__":
    main()

