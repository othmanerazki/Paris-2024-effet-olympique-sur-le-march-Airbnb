import pandas as pd
import s3fs
from urllib.parse import quote

fs = s3fs.S3FileSystem(
    anon=True, client_kwargs={"endpoint_url": "https://minio.lab.sspcloud.fr"}
)

files = fs.find("etiennealpy/données paris")

# On vérifie que tous les fichiers ont bien été trouvés

print(len(files), "ont été trouvés")

dfs = {}
for f in files:
  if f.lower().endswith(".csv"):
    url = f"https://minio.lab.sspcloud.fr/{quote(f, safe='/')}"
    name = f.split("/")[-1]
    try:
      dfs[name] = pd.read_csv(url)
    except Exception as e:
      print(e)

#On vérifie que tous les tableaux ont bien le même format

columns_dict = {}
for name, df in dfs.items():
  columns_dict[name] = list(df.columns)

reference_cols = list(columns_dict.values())[0] if columns_dict else []

all_match = True
for name, cols in columns_dict.items():
  if cols != reference_cols:
    all_match = False
    print(f"Différent : {name}")

if all_match and columns_dict:
  print("Tous les fichiers ont les mêmes colonnes.")

for name, df in dfs.items():
  print(f"--- {name} ---")
  print(df.head(2))