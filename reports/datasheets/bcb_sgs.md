# Datasheet — Séries Selic (SGS 11) e IPCA (SGS 433) do Banco Central do Brasil

## 1. Motivação
- Por que foi criado? Para qual tarefa? O Sistema Gerenciador de Séries Temporais (SGS) do BCB publica séries econômicas como dados abertos. Neste projeto, a Selic diária (11) é o benchmark de rentabilidade e o IPCA mensal (433) corrige o Tesouro IPCA+ e deflaciona o retorno real.
- Quem criou e quem financiou? Banco Central do Brasil (Selic: taxa de juros, % a.d.; IPCA: variação mensal, calculada originalmente pelo IBGE).

## 2. Composição
- O que cada instância representa? Selic: taxa diária (% a.d.) por dia útil. IPCA: variação percentual mensal do índice.
- Número de instâncias e período coberto: Selic 6.229 linhas, de 02/01/2002 a 16/10/2026; IPCA 297 meses, de 01/2002 a 09/2026 (execução de 17/10/2026).
- Campos, tipos e contrato: `src/schemas/macro.py` (`reference_date: Date`, `value: Float64` em % entre −5 e 50, sem nulos).
- Rótulo: não há.
- Dados ausentes (taxa por coluna): o contrato proíbe nulos na camada silver. TODO(owner): registrar quantas linhas foram descartadas na limpeza.
- Campos sensíveis / PII e tratamento: nenhum.
- É amostra de uma população maior? Como amostrado? Não; série completa a partir de 01/01/2002 (início do histórico do Tesouro Direto).

## 3. Processo de coleta
- Fonte(s) e sistema(s) de origem: API JSON `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{11,433}/dados`, consultada em janelas de até 9 anos (a API limita consultas diárias a 10 anos).
- Período e frequência de coleta: sob demanda, com cache de 24 h e snapshot novo apenas se o SHA-256 mudar.
- Consentimento / aviso aos titulares: não aplicável.

## 4. Pré-processamento
- Limpeza, filtragem e linhas removidas por regra: parsing de datas `dd/mm/aaaa` e valores, deduplicação e validação Pandera (`clean_sgs`). TODO(owner): registrar o número de linhas removidas por regra.
- Anonimização / pseudonimização: não aplicável.
- Hash SHA-256 dos dados brutos: Selic `74e0773bb152d3aa0c4550f63acc2bc27f2c51be45c40245f875e3734803519a` (280.305 bytes, 2026-10-17T21:47:06Z); IPCA `ec9b6ce0159e9d8ab2e5d551ee010f83b0c337de58daea8fb4db8c9cbd0172ce` (12.193 bytes, 2026-10-17T21:47:52Z). Manifestos em `data/bronze/bcb_sgs_11/` e `data/bronze/bcb_sgs_433/`.

## 5. Usos
- Usos pretendidos: benchmark Selic e deflator IPCA em simulações educacionais.
- Usos desaconselhados: previsão de inflação ou de juros (valores após o último dado são premissas do usuário); uso fiscal ou contratual.
- Riscos de viés conhecidos: o IPCA mensal pode ser revisado e tem defasagem de publicação; o último mês parcial é rateado por dias corridos.

## 6. Distribuição
- Licença e restrições: dado aberto do BCB. TODO(owner): confirmar os termos de uso do portal de dados abertos antes de redistribuir.
- Onde está armazenado (DVC remote, bucket): localmente em `data/bronze/` (fora do Git); sem DVC remote.

## 7. Manutenção
- Responsável: Luan Freitas.
- Frequência de atualização: sob demanda (`make ingest`); a Selic atualiza diariamente e o IPCA, mensalmente.
- Como atender pedidos de exclusão de titulares: não aplicável.

## 8. LGPD
- Base legal (art. 7 / art. 11): não há tratamento de dados pessoais; séries macroeconômicas públicas.
- Prazo de retenção: enquanto o projeto existir; reconstruível a partir da API.
- Relatório de impacto (RIPD) necessário? Não.
