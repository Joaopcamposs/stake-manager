# Bet Tracker — Documentação de Produto

## Visão Geral

Bet Tracker é uma aplicação web pessoal para registro e acompanhamento de apostas esportivas. Permite controlar banca, registrar apostas com mercados específicos, acompanhar resultados e visualizar métricas de desempenho.

## Funcionalidades

### Autenticação
- Login com senha única (configurável via variável de ambiente)
- Sessão persistente via cookie (30 dias)
- Logout manual

### Registro de Apostas
- Criação simultânea de aposta **Principal** e **Zoião** no mesmo jogo
- Campos por aposta:
  - Mercado (Over 0.5–8.5 + Asiático 1–8 para principal; Asiático 1–8 para zoião)
  - Valor (stake)
  - Odd (entrada sem ponto aceita: "155" → 1.55)
  - Resultado (green/red/void/pendente) — independente por tipo
- Campo compartilhado: jogo (opcional), data
- Cálculo automático de retorno (atualiza em tempo real)

### Edição e Exclusão
- Editar qualquer campo de uma aposta existente
- Alterar resultado a qualquer momento
- Excluir aposta com confirmação

### Home
- KPIs do dia: total apostas, greens, reds, lucro do dia
- Botão centralizado "+ Nova Aposta"
- Lista de apostas pendentes (clicável → editar)
- Histórico recente (últimas 20 resolvidas) com lucro por aposta
- Badges: tipo (principal/zoião), mercado, resultado (green/red/void)
- Cada linha mostra: stake @ odd → lucro

### Dashboard
- **Filtros**: período (7d / 30d / 90d / todo) + tipo (todos / principal / zoião)
- **KPIs** (13 cards):
  - Banca Atual (valor corrente, colorido verde/vermelho)
  - Variação % (lucro/banca inicial, colorido)
  - Total Apostado (soma stakes resolvidas)
  - Lucro Líquido (retorno - stakes, colorido)
  - ROI (lucro/total apostado %)
  - Taxa de Acerto (greens/total resolvidos %)
  - Odd Média Ponderada (ponderada por stake)
  - Breakeven (1/odd média %, mínimo pra empatar)
  - Edge (taxa acerto - breakeven, destacado com borda azul, colorido)
  - Streak Atual (sequência green/red corrente)
  - Drawdown Máximo (queda máxima desde pico)
  - Total Apostas (número de apostas resolvidas no período)
  - Stake Médio (total apostado / total apostas)
- **Gráficos** (7):
  - Banca ao Longo do Tempo (line, com linha tracejada da banca inicial real do settings)
  - Lucro Acumulado por Tipo (line, principal vs zoião)
  - Evolução Mensal (bar, lucro por mês, verde/vermelho)
  - Lucro por Mercado (bar, ordenado por lucro, labels legíveis)
  - Distribuição de Odds (bar, buckets de 0.1)
  - Taxa de Acerto por Faixa de Odd (bar, % por bucket)
  - Resultado por Dia da Semana (bar, verde/vermelho conforme lucro)

### Configurações
- Banca inicial (base pra cálculos de variação e drawdown)
- Stakes padrão (principal e zoião, usados como default no modal)
- Odd mínima

## Fluxo Principal

1. Login → Home
2. "+ Nova Aposta" → Modal com campos principal + zoião
3. Preencher mercado, odd, resultado → Salvar
4. Aposta aparece na lista (pendente ou resolvida conforme resultado)
5. Clicar na aposta → Editar/Excluir

## Regras de Negócio

- Pelo menos uma aposta (principal ou zoião) deve ter odd preenchida
- Resultado "green": retorno = stake × odd
- Resultado "red": retorno = 0
- Resultado "void": retorno = stake (devolução)
- Zoião aceita apenas mercados asiáticos (inteiros: 1–8)
- Odd sem ponto é auto-convertida ("155" → "1.55", "23" → "2.3")
- Ordenação por uuid7 (temporal descendente)
