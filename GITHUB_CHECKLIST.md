# Checklist de publicação no GitHub

## Antes do primeiro commit

```text
[ ] README.md revisado
[ ] docs/ revisado
[ ] .gitignore presente
[ ] .env NÃO versionado
[ ] .env.example presente
[ ] requirements.txt gerado com pip freeze
[ ] dados brutos fora do repositório
[ ] outputs pesados fora do repositório
[ ] nenhum usuário/senha em scripts
[ ] screenshot do dashboard incluído
```

## Comandos sugeridos

Na raiz do projeto:

```powershell
git init
git status
git add README.md docs .gitignore .env.example requirements.txt src sql
git status
git commit -m "Publica versão consolidada do VerdePrioriza"
```

Depois de criar um repositório vazio no GitHub:

```powershell
git branch -M main
git remote add origin URL_DO_REPOSITORIO
git push -u origin main
```

## Antes do push

Execute:

```powershell
git status
```

e confirme que arquivos como estes NÃO aparecem:

```text
.env
data/raw/
outputs/
*.backup
```

## Sugestão de descrição curta do repositório

> Sistema de priorização territorial ambiental com Python, PostgreSQL/PostGIS, dados públicos, análise espacial, explicabilidade e dashboard Streamlit.
