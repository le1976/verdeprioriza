# Arquitetura do VerdePrioriza

## 1. Objetivo da arquitetura

A arquitetura foi desenhada para separar claramente:

- origem dos dados;
- ingestão;
- tratamento;
- modelagem;
- análise espacial;
- validação;
- publicação.

Essa separação facilita auditoria, manutenção e reprodução dos resultados.

---

## 2. Banco de dados

O banco utiliza PostgreSQL com PostGIS.

Schemas principais:

```text
raw
staging
core
spatial
analytics
```

### raw
Recebe dados com o mínimo de transformação possível.

### staging
Camada intermediária para limpeza, agregação e padronização.

### core
Entidades consolidadas do projeto, como dimensões municipais.

### spatial
Geometrias, células, áreas prioritárias e objetos territoriais.

### analytics
Indicadores, views analíticas, relatórios e camadas consolidadas para consumo.

---

## 3. Fluxo de dados

```text
Fontes externas
     ↓
raw
     ↓
staging
     ↓
core / spatial
     ↓
analytics
     ↓
relatórios / mapas / dashboard
```

---

## 4. Componentes analíticos

### IPA
Indicador de pressão ambiental em escala municipal.

### IPL
Indicador de prioridade local, calculado sobre unidades espaciais.

### Prioridade Integrada
Combina contexto municipal e local em um indicador operacional de ordenação.

---

## 5. Seleção espacial

A seleção territorial final utiliza:

- núcleo prioritário;
- suporte espacial;
- faixa excepcional;
- critérios mínimos de área;
- distância máxima de suporte;
- robustez;
- ranking.

Versão territorial consolidada:

```text
areas_9h_v1.1_2024
```

---

## 6. Validação espacial

A etapa 9I verifica, entre outros pontos:

- validade geométrica;
- pertencimento ao município;
- presença de núcleo;
- consistência da área;
- coerência dos percentuais;
- limites de prioridade;
- ranking;
- distância do suporte;
- sobreposição.

A auditoria final foi aprovada sem inconsistências nos controles utilizados.

---

## 7. Camadas de publicação

```text
10A → ficha técnica individual
10B → relatório executivo municipal
10C → explicabilidade
10D → dashboard final integrado
```

Cada camada consome resultados já validados, evitando recalcular a lógica central na interface.
