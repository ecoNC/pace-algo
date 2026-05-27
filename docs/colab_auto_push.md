# Colab → GitHub Auto-Push Pattern

Wiederverwendbares Pattern, das jedes Notebook (NB12, NB13, NB14, ...) am Ende benutzt, um seine `/results/`-Outputs automatisch von Colab nach GitHub zu pushen. Damit muss Nico nichts manuell aus Drive runterladen, und der Sibling-Claude sieht Ergebnisse sofort.

**Erstmalig implementiert in:** NB12 Section 11 (2026-05-27)

---

## One-Time Setup (einmal pro Anthropic-Account / Colab-Workspace)

### 1. GitHub Personal Access Token erzeugen

1. https://github.com/settings/personal-access-tokens (Fine-grained tokens)
2. Generate new token
3. **Repository access:** Only select repositories → `ecoNC/pace-algo`
4. **Permissions** → Repository permissions:
   - **Contents: Read and write** (nötig für push)
   - Alle anderen: leer lassen (Principle of Least Privilege)
5. **Expiration:** 90 Tage (oder maximal 365)
6. Generate → Token kopieren (wird nur einmal angezeigt!)

### 2. Token in Colab Secrets ablegen

1. Notebook in Colab öffnen
2. Links in der Sidebar: **🔑 Secrets-Icon** (Schlüssel-Symbol)
3. "Add new secret"
4. Name: `GITHUB_TOKEN`
5. Value: `<den eben kopierten Token>`
6. Toggle **"Notebook access"** für das gewünschte Notebook AN

### 3. Token-Renewal nach Ablauf

Wenn Token abläuft (Push schlägt fehl mit 401):
- Schritt 1 wiederholen (neuen Token erzeugen)
- In Colab Secrets den `GITHUB_TOKEN`-Wert überschreiben
- Notebooks müssen nicht angepasst werden

---

## Code-Snippet für neue Notebooks

Am Ende jedes Notebooks, nach der Export-zu-`/results/`-Cell, diese zwei Cells einfügen:

### Markdown-Cell

```markdown
## N+1. Auto-Push Results to GitHub (Optional)

Pusht die Section-N-Results direkt nach github.com/ecoNC/pace-algo.
Setup-Doku: /docs/colab_auto_push.md
```

### Code-Cell

```python
import shutil, subprocess
from pathlib import Path as _P

if not IS_COLAB:
    print('Local run — skip auto-push (files already in repo).')
else:
    try:
        from google.colab import userdata
        GH_TOKEN = userdata.get('GITHUB_TOKEN')
    except Exception as e:
        GH_TOKEN = None
        print(f'ERROR: cannot read GITHUB_TOKEN: {e}')
        print('Setup: see /docs/colab_auto_push.md')

    if GH_TOKEN:
        NB_TAG         = 'nbXX'  # <-- ANPASSEN pro Notebook (nb12, nb13, etc.)
        REPO_URL_HTTPS = 'github.com/ecoNC/pace-algo.git'
        TMP_REPO       = _P('/tmp/pace-algo-push')

        if TMP_REPO.exists():
            shutil.rmtree(TMP_REPO)
        subprocess.run(['git', 'clone', '--quiet',
                        f'https://{GH_TOKEN}@{REPO_URL_HTTPS}', str(TMP_REPO)], check=True)
        subprocess.run(['git', '-C', str(TMP_REPO), 'config', 'user.name', 'ecoNC'], check=True)
        subprocess.run(['git', '-C', str(TMP_REPO), 'config', 'user.email',
                        'ecoNC@users.noreply.github.com'], check=True)

        copied = []
        for f in sorted(RESULTS_DIR.rglob(f'*{RUN_DATE}*')):
            if not f.is_file(): continue
            rel = f.relative_to(RESULTS_DIR)
            dest = TMP_REPO / 'results' / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            copied.append(rel)

        subprocess.run(['git', '-C', str(TMP_REPO), 'pull', '--rebase', '--quiet',
                        'origin', 'main'], check=True)
        subprocess.run(['git', '-C', str(TMP_REPO), 'add', 'results/'], check=True)
        msg = f'{NB_TAG.upper()} results: run {RUN_DATE} ({len(copied)} files)'
        subprocess.run(['git', '-C', str(TMP_REPO), 'commit', '-m', msg], check=True)
        subprocess.run(['git', '-C', str(TMP_REPO), 'push', 'origin', 'main'], check=True)

        sha = subprocess.run(['git', '-C', str(TMP_REPO), 'rev-parse', '--short', 'HEAD'],
                              capture_output=True, text=True).stdout.strip()
        print(f'✓ Pushed {len(copied)} files as ecoNC ({sha})')
        print(f'  https://github.com/ecoNC/pace-algo/commit/{sha}')

        shutil.rmtree(TMP_REPO)
```

**Was anpassen pro Notebook:**
- `NB_TAG = 'nbXX'` — die Notebook-Nummer
- (Optional) Commit-Message-Body — Notebook-spezifische Details

Alle anderen Felder bleiben gleich, weil sie aus dem Notebook-Setup-Block kommen (`IS_COLAB`, `RESULTS_DIR`, `RUN_DATE`).

---

## Sicherheits-Überlegungen

1. **Token NIE im Notebook-File hardcoded.** Immer über `userdata.get()` aus Colab Secrets.
2. **Token wird NIE committed.** Der clone benutzt Token in URL nur im RAM, das Working-Tree-Repo wird am Ende komplett gelöscht (`shutil.rmtree`).
3. **Fine-grained Token mit nur `Contents: Read and write`** — kann nichts anderes manipulieren (keine Issues, kein Settings, keine anderen Repos).
4. **Repository-scoped** — Token ist nur für `ecoNC/pace-algo` gültig.
5. **Commit-Author IMMER ecoNC** — Privacy-Lock (HANDOFF Section 12.4.19). Real-Name von Nico ist NICHT in Commit-History.

## Was nicht gepusht wird

- Notebook-Cell-Outputs (Privacy + Diff-Größe)
- `artifacts/models/*.pkl` (zu groß, lokal-only)
- `data_cache/` (zu groß)
- Nur Files matching `*{RUN_DATE}*` aus `/results/` (also nur die Outputs von DIESEM Run)

## Conflict-Handling

- Vor jedem Push wird `git pull --rebase` ausgeführt
- Wenn Sibling-Claude parallel etwas committet hat das die `/results/`-Files anfasst (unwahrscheinlich, weil Notebook-Runs sind exklusiv), schlägt rebase mit Konflikt fehl
- Notebook stoppt dann mit klarer Fehlermeldung → Nico muss manuell intervenieren
- KEIN silent overwrite, KEIN force-push
