# Datasheet — Taxas dos Títulos Ofertados pelo Tesouro Direto (Tesouro Transparente)

## 1. Motivação
- Por que foi criado? Para qual tarefa? O Tesouro Nacional publica o histórico de preços e taxas dos títulos por transparência e uso público. Neste projeto alimenta a curva de juros (taxa × prazo) e a taxa de compra usada nas simulações.
- Quem criou e quem financiou? Tesouro Nacional (governo federal). TODO(owner): confirmar o nome oficial do órgão publicador na página do conjunto de dados.

## 2. Composição
- O que cada instância representa? Uma cotação diária de um título (tipo + vencimento + data-base).
- Número de instâncias e período coberto: 177.434 linhas na camada silver, de 31/12/2004 a 15/10/2026 (execução de 17/10/2026). Gold `yield_curve.parquet`: 47.157 linhas (28.215 Prefixado; 18.942 IPCA+).
- Campos, tipos e contrato: `src/schemas/treasury.py` (`bond_type`, `maturity_date`, `reference_date`, `buy_rate`, `sell_rate`, `buy_price`, `sell_price`, `base_price`; taxas em % a.a. entre −10 e 60; preços ≥ 0; chave única `bond_type + maturity_date + reference_date`).
- Rótulo: não há; dados de mercado observados.
- Dados ausentes (taxa por coluna): TODO(owner): calcular a taxa de nulos de `buy_rate`, `sell_rate`, `buy_price`, `sell_price` e `base_price`.
- Campos sensíveis / PII e tratamento: nenhum; dados de mercado, sem pessoas.
- É amostra de uma população maior? Como amostrado? Não; é o histórico completo publicado. Na camada gold, apenas Prefixado e IPCA+ (títulos "bullet") são mantidos.

## 3. Processo de coleta
- Fonte(s) e sistema(s) de origem: CSV `PrecoTaxaTesouroDireto.csv` do portal [Tesouro Transparente](https://www.tesourotransparente.gov.br) (URL em `configs/config.yaml`; separador `;` e decimal com vírgula).
- Período e frequência de coleta: o portal atualiza diariamente; o pipeline respeita um cache de 24 h e só cria novo snapshot se o SHA-256 mudar.
- Consentimento / aviso aos titulares: não aplicável (sem titulares).

## 4. Pré-processamento
- Limpeza, filtragem e linhas removidas por regra: conversão de tipos e decimais, deduplicação e validação Pandera em `src/preprocessing/cleaning.py`. TODO(owner): registrar o número de linhas removidas por regra.
- Anonimização / pseudonimização: não aplicável.
- Hash SHA-256 dos dados brutos: `f4f9b0fb9a1850da4cbca47d5b896464c04b21b302cf591de178726a426e2972` (snapshot de 2026-10-17T21:46:55Z, 14.598.768 bytes; `data/bronze/tesouro_transparente/20261017T214655Z/manifest.json`).

## 5. Usos
- Usos pretendidos: construção da curva de juros histórica; taxa de compra de referência para simulação educacional.
- Usos desaconselhados: execução de ordens ou decisões de investimento (as taxas do CSV são as "da manhã" e a execução real pode ocorrer a outro preço).
- Riscos de viés conhecidos: não há viés sobre pessoas; há mudança do catálogo de títulos ao longo do tempo (só entram os títulos ofertados em cada data).

## 6. Distribuição
- Licença e restrições: dado aberto governamental. TODO(owner): confirmar a licença exata no portal antes de redistribuir.
- Onde está armazenado (DVC remote, bucket): localmente em `data/bronze/` (fora do Git); sem DVC remote neste projeto.

## 7. Manutenção
- Responsável: Luan Freitas.
- Frequência de atualização: sob demanda (`make ingest`), com cache de 24 h.
- Como atender pedidos de exclusão de titulares: não aplicável (sem dados pessoais).

## 8. LGPD
- Base legal (art. 7 / art. 11): não há tratamento de dados pessoais; dados públicos de mercado.
- Prazo de retenção: enquanto o projeto existir; snapshots são reconstruíveis a partir da fonte.
- Relatório de impacto (RIPD) necessário? Não.
