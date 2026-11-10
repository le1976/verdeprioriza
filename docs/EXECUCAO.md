# Guia de execução

## 1. Pré-requisitos

- Windows
- Python
- PostgreSQL 17
- PostGIS
- pgAdmin 4

Diretório de trabalho usado no desenvolvimento:

```text
C:\verde_prioriza
```

---

## 2. Ambiente virtual

Exemplo:

```powershell
cd C:\verde_prioriza
.\.venv\Scripts\Activate.ps1
```

---

## 3. Variáveis de ambiente

O projeto utiliza `.env` para parâmetros de conexão.

Exemplo de estrutura, sem valores reais:

```text
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=5432
```

Nunca publique esse arquivo.

---

## 4. Dependências

Para registrar exatamente o ambiente instalado na máquina de desenvolvimento:

```powershell
pip freeze > requirements.txt
```

Essa abordagem é preferível a inventar versões manualmente.

---

## 5. Execução dos módulos finais

### 10B

Executar o SQL correspondente no banco e depois:

```powershell
python src/reporting/gerar_relatorio_executivo_10b.py
```

### 10C

```powershell
python src/reporting/gerar_explicabilidade_10c.py
```

### 10D

```powershell
streamlit run src/dashboard/dashboard_final_10d.py
```

---

## 6. Views principais dos módulos finais

```text
analytics.vw_ficha_area_10a
analytics.vw_resumo_municipio_10b
analytics.vw_resumo_geral_10b
analytics.vw_explicabilidade_area_10c
analytics.vw_explicabilidade_municipio_10c
analytics.vw_dashboard_area_10d
analytics.vw_dashboard_municipio_10d
```

---

## 7. Produtos de saída

### Fichas 10A

```text
outputs/reports/module10a/
```

### Relatório 10B

```text
outputs/reports/module10b/
```

### Explicabilidade 10C

```text
outputs/reports/module10c/
```

### Mapas 9I

```text
outputs/maps/module9i/
```

---

## 8. Checklist de validação

Antes de publicar:

```text
[ ] Banco conecta corretamente
[ ] PostGIS ativo
[ ] 1.045 áreas finais
[ ] 20 municípios
[ ] 0 geometrias ausentes no dashboard
[ ] 1.045 fichas 10A
[ ] 1.045 explicações 10C
[ ] mapas 9I disponíveis
[ ] dashboard abre sem erro
[ ] .env não está versionado
```
