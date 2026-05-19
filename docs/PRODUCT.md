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
  - Mercado (Over 0.5–8.5 para principal; Asiático 1.0–8.0 para ambos)
  - Valor (stake)
  - Odd
  - Resultado (green/red/void/pendente) — independente por tipo
- Campo compartilhado: jogo (opcional), data
- Cálculo automático de retorno

### Edição e Exclusão
- Editar qualquer campo de uma aposta existente
- Alterar resultado a qualquer momento
- Excluir aposta com confirmação

### Home
- KPIs do dia: total apostas, greens, reds, lucro
- Lista de apostas pendentes
- Histórico recente (últimas 20 resolvidas)
- Badges: tipo (principal/zoião), mercado, resultado

### Dashboard
- Gráficos de desempenho (Chart.js)
- Filtros por período e tipo

### Configurações
- Banca inicial
- Stakes padrão (principal e zoião)
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
- Zoião aceita apenas mercados asiáticos
- Ordenação por uuid7 (temporal descendente)
