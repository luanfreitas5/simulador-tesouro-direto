# Simulador do Tesouro Direto

Curva de juros histórica do Tesouro Direto e simulador de rentabilidade **bruta, líquida e real**.

- Dados: Tesouro Transparente (preços e taxas) e BCB SGS (Selic e IPCA).
- Módulo financeiro puro e determinístico, com alíquotas e taxas configuráveis.
- App Streamlit com a curva navegável por data e o simulador.

> Projeto educacional. Confira as regras vigentes de IR, custódia e IOF antes de usar os resultados.

## Início rápido

```bash
make install-app
make pipeline
make app
```

Veja [Premissas e limitações](premissas.md) e a [referência da API](api.md).
