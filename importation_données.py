import pandas as pd
import s3fs
from urllib.parse import quote


def charger_donnees_paris():
  fs = s3fs.S3FileSystem(
      anon=True, client_kwargs={"endpoint_url": "https://minio.lab.sspcloud.fr"}
  )
  files = fs.find("etiennealpy/données paris")

  mois_disponibles = [
      "janvier",
      "fevrier",
      "mars",
      "avril",
      "mai",
      "juin",
      "juillet",
      "aout",
      "septembre",
      "octobre",
      "novembre",
      "decembre",
  ]

  dfs = {}
  for f in files:
    nom_fichier = f.split("/")[-1].lower()
    if "listing_" in nom_fichier:
      url = f"https://minio.lab.sspcloud.fr/{quote(f, safe='/')}"
      mois_trouve = "inconnu"
      for m in mois_disponibles:
        if m in nom_fichier:
          mois_trouve = m
          break
      try:
        dfs[mois_trouve] = pd.read_csv(url)
      except Exception as e:
        print(e)

  return dfs


if __name__ == "__main__":
  dfs = charger_donnees_paris()
  print(f"{len(dfs)} tableaux chargés avec succès !")
  print(list(dfs.keys()))