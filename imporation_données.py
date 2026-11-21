import pandas as pd
import s3fs
from urllib.parse import quote

#Cette méthode permet de télécharger les données directement depuis mon bucket privé sur SSP Cloud
#Pas besoin de se les transférer par mail donc

fs = s3fs.S3FileSystem(
    anon=True, client_kwargs={"endpoint_url": "https://minio.lab.sspcloud.fr"}
)

#Je vérifie que tous les fichiers ont été trouvés (il y en a 12 normalement)
files = fs.find("etiennealpy/données paris")
print(len(files))

dfs = {}
for f in files:
  if f.lower().endswith(".csv"):
    try:
      url = f"https://minio.lab.sspcloud.fr/{quote(f, safe='/')}"
      name = f.split("/")[-1]
      dfs[name] = pd.read_csv(url)
      print(name)
    except Exception as e:
      print(e)

#Une dernière petite vérification : est-ce que tous les fichiers sont différents ?

for name, df in dfs.items():
  print(f"--- {name} ---")
  print(df.head(2))