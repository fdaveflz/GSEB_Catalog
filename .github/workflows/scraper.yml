name: 🔄 Actualizar Catálogo IMUSA

on:
  # ── Horario automático ──────────────────────────────
  schedule:
    - cron: '0 6 * * *'    # Todos los dias a las 6am

  # ── También se puede correr manualmente ─────────────
  workflow_dispatch:

jobs:
  scrape-and-update:
    runs-on: ubuntu-latest

    steps:
      # 1. Descargar el código del repositorio
      - name: 📥 Checkout repositorio
        uses: actions/checkout@v3

      # 2. Configurar Python
      - name: 🐍 Configurar Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      # 3. Instalar dependencias
      - name: 📦 Instalar dependencias
        run: pip install -r requirements.txt

      # 4. Correr el scraper
      - name: 🕷️ Correr scraper
        run: python scraper.py

      # 5. Subir el JSON actualizado al repositorio
      - name: 💾 Guardar JSON actualizado
        run: |
          git config --global user.name  "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add all_products.json *.json
          git diff --staged --quiet || git commit -m "🔄 Catálogo actualizado $(date '+%Y-%m-%d %H:%M')"
          git push
