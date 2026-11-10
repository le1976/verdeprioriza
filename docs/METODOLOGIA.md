# Metodologia

## 1. Princípio geral

O VerdePrioriza trabalha com **priorização relativa**, não com determinação legal de passivos ambientais.

Scores maiores indicam maior prioridade relativa dentro do universo analisado.

---

## 2. Referência temporal

A versão consolidada utiliza **2024** como ano de referência.

Essa escolha evita misturar períodos ainda incompletos ou não consolidados entre diferentes fontes.

---

## 3. Indicadores municipais

O componente municipal sintetiza pressões ambientais relativas.

Entre os sinais utilizados no desenvolvimento do projeto estão:

- menor cobertura natural;
- perda de vegetação;
- pressão agropecuária;
- fogo recente;
- carga de fogo.

Os indicadores são normalizados para comparação relativa.

---

## 4. Indicadores locais

O componente local considera atributos espaciais como:

- hidrologia;
- conectividade;
- declividade;
- elegibilidade territorial;
- contexto de vegetação;
- distância de drenagem.

---

## 5. Normalização

O projeto utiliza normalização relativa por ranking/percentil em etapas analíticas.

Portanto:

```text
0   → menor pressão/prioridade relativa
100 → maior pressão/prioridade relativa
```

Isso não significa ausência ou presença absoluta de problema ambiental.

---

## 6. Priorização espacial

Após o cálculo do IPL e da Prioridade Integrada, a seleção territorial utiliza limiares derivados da distribuição observada.

Limiar de suporte:

```text
PI >= 55,84
```

Núcleo:

```text
PI >= 58,44
```

Faixa excepcional:

```text
PI >= 61,46
```

A faixa excepcional é informativa e está contida no núcleo.

---

## 7. Critérios operacionais

A formação das áreas finais utiliza:

- núcleo;
- suporte;
- distância máxima de 500 m entre suporte e núcleo;
- área operacional mínima de 10 ha.

---

## 8. Robustez

A robustez é utilizada para indicar estabilidade relativa da priorização.

Na versão final:

```text
Alta   → amplitude <= 7,04
Média  → 7,04 < amplitude <= 9,18
Baixa  → amplitude > 9,18
```

---

## 9. Produtos finais

A seleção final resultou em:

- 1.045 áreas;
- 20 municípios;
- 51.810,1 ha;
- 37.443,5 ha de núcleo;
- 14.366,5 ha de suporte;
- 18.766,8 ha de faixa excepcional.

---

## 10. Explicabilidade

A explicabilidade da 10C não é causal.

Ela descreve:

- quais componentes possuem maior score;
- como a área se compara ao conjunto;
- sua posição no ranking;
- seu contexto municipal;
- sua robustez;
- sua composição territorial.

Isso permite interpretar o resultado sem afirmar causalidade indevida.
