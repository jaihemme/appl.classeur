SWIFTOCR="/Users/yogi/Docker/appl.classeur/swiftocr" \
SWIFTOCR_DIR="/Users/yogi/Docker/appl.classeur/test/mobilière" \
python swiftocr_server.py

DATA='{"file":"Décompte de prime pour la police numéro G-0175-8064 2024 - DEMENAGEMENT.pdf",
       "lang":"fr-FR",
       "pages":"1"}'

curl -sS http://localhost:8765/ocr   -H "Content-Type: application/json"   -d"$DATA" | jq -r '.stdout' 
