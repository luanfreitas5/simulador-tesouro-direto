# Model Card — Simulador de rentabilidade do Tesouro Direto v0.1.0

**Status:** DRAFT
**Bloqueios pendentes:** (a) validação externa contra o simulador oficial do Tesouro Direto — bloqueia qualquer uso que não seja educacional/demonstração; (b) análise de sensibilidade quantificada a IPCA e Selic projetados — bloqueia conclusões comparativas entre títulos; (c) arquivo `reports/metrics/*.json` versionado — bloqueia a reprodutibilidade auditável dos números do README.

> Este artefato **não é um modelo de aprendizado de máquina**: é um modelo financeiro determinístico (sem treino, sem parâmetros estimados). As seções típicas de ML (treino, calibração, fairness) são mantidas e respondidas como "não aplicável", com justificativa.

## 1. Detalhes do modelo
- **Responsável / contato:** Luan Freitas — luan.mgf@gmail.com
- **Data:** 2026-10-26
- **Algoritmo:** capitalização em dias úteis (base 252) para Tesouro Prefixado e IPCA+ (bullet), IR regressivo sobre o rendimento, custódia B3 de 0,20% a.a. e rentabilidade real por Fisher (`src/finance/`). Benchmark: Selic diária observada + Selic anual projetada.
- **Rastreabilidade:** Git SHA `4d360d1` (base; há alterações locais não commitadas na escrita) · MLflow run: não aplicável (sem treino) · hash dos dados: SHA-256 dos snapshots bronze em `data/bronze/*/<timestamp>/manifest.json` (ver [datasheets](../datasheets/))
- **Licença:** MIT

## 2. Uso pretendido
- **Uso primário:** apoiar a comparação educacional entre Tesouro Prefixado, Tesouro IPCA+ e Selic, mostrando rentabilidade bruta, líquida e real ao vencimento.
- **Usuários pretendidos:** estudantes, avaliadores de portfólio e investidores pessoa física que queiram entender o efeito de IR, custódia e inflação.
- **Humano no circuito:** sim. O resultado é informativo; qualquer decisão de investimento exige conferir as regras vigentes em fontes oficiais.

## 3. Usos fora do escopo
- Recomendação de investimento ou decisão automática de compra/venda.
- Resgate antecipado, marcação a mercado, IOF (< 30 dias), cupons semestrais e Tesouro Selic como título simulado.
- Previsão de IPCA ou Selic futuros: os valores projetados são **premissas do usuário**, não previsões.
- Cálculo de imposto devido para fins fiscais ou contábeis.
- Datas de compra anteriores ao início do histórico (31/12/2004 para o Tesouro; 01/2002 para Selic/IPCA).

## 4. Fatores
- **Grupos relevantes:** tipo de título (Prefixado, IPCA+), prazo até o vencimento (faixas do IR: ≤180, 181–360, 361–720, >720 dias), parcela do período já observada vs. projetada.
- **Ambientes:** regras tributárias e taxas vigentes no momento do cálculo (configuráveis em `configs/finance.yaml`); calendário sem feriados nacionais.

## 5. Métricas
- **Métrica principal:** rentabilidade **líquida e real anualizada** — justificativa: é o que o investidor recebe depois de IR, custódia e inflação; comparar o bruto superestima o retorno.
- **Limiar de decisão:** não aplicável (não há classificação).
- **Calibração:** não aplicável. Em seu lugar, verificação de correção: testes nas fronteiras do IR (180/181, 360/361, 720/721), propriedades `hypothesis` (líquido ≤ bruto; líquido monotônico no rendimento; IR não cresce com o prazo) e ausência de IR em prejuízo.

## 6. Dados de avaliação
Não há conjunto de avaliação com rótulos. TODO(owner): comparar ao menos 3 simulações com o simulador oficial do Tesouro Direto e registrar a diferença absoluta e relativa.

## 7. Dados de treino
Não há treino. Os insumos são Tesouro Transparente (taxas/PUs) e BCB SGS (Selic, IPCA): ver [Datasheet Tesouro Transparente](../datasheets/tesouro_transparente.md) e [Datasheet BCB SGS](../datasheets/bcb_sgs.md).

## 8. Análise quantitativa
Exemplos de 15/10/2026 (R$ 10.000, mantido até o vencimento; IPCA 4,5% a.a. e Selic 12% a.a. assumidos após o último dado):

| Recorte | n | Métrica (líquido a.a.) ± IC 95% | Baseline (Selic) |
|---|---|---|---|
| Prefixado 2029 (12,64%) | 1 simulação | 11,04% (real 6,26%); sem IC (determinístico) | 10,47% |
| IPCA+ 2035 (IPCA + 6,84%) | 1 simulação | 10,47% (real 5,71%); sem IC (determinístico) | 10,97% |

TODO(owner): análise de sensibilidade (grade de IPCA e Selic projetados) com a faixa de resultados por título e a fronteira em que a ordem entre os títulos se inverte.

## 9. Considerações éticas e fairness
- **Atributos sensíveis auditados:** nenhum. O modelo não usa dados pessoais nem atributos de indivíduos; as saídas dependem apenas de título, datas, valor e parâmetros públicos.
- **Disparidades encontradas:** não aplicável.
- **Mitigação aplicada:** não aplicável.
- **Risco ético principal:** o usuário interpretar a simulação como recomendação ou promessa de retorno. Mitigado por avisos no README e no app.
- **Base legal LGPD:** não há tratamento de dados pessoais.

## 10. Limitações, riscos e monitoramento
- **Limitações conhecidas:** calendário sem feriados (dias úteis ligeiramente superestimados); IPCA+ com rateio por dias corridos (diferenças pequenas ante o VNA oficial); custódia simplificada (saldo médio rateado por dia corrido, sem cobrança semestral real nem isenções); a taxa "da manhã" do CSV pode diferir da execução efetiva; sem IOF.
- **Mudanças de distribuição previstas:** alteração de alíquotas ou da taxa de custódia por lei/regulamento; mudança de formato ou URL do CSV do Tesouro Transparente; revisões do IPCA publicadas pelo BCB.
- **Monitoramento:** contratos `pandera` em cada fronteira bronze → silver → gold (falham cedo); CI semanal; revisão manual das alíquotas a cada mudança regulatória.
- **Critério de retreino / descontinuação:** não há retreino. Rever o modelo quando a regra tributária ou as tarifas mudarem, ou se a comparação com o simulador oficial divergir além de uma tolerância. TODO(owner): definir a tolerância.
