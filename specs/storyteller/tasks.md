# Tasks — Storyteller

| # | Cartão | Arquivos | Aceite |
|---|--------|----------|--------|
| T1 | Persona ouvinte pt-BR | server/src/agent.py | Nova: pt-BR STT/TTS, pergunta 1x por turno, greeting BR |
| T2 | Cliente feita + jobs | server/src/feita.py | session+msg+poll+render; sem lib nova (httpx já tem? checar) |
| T3 | Endpoints /api/film | server/src/server.py | POST cria job; GET status; compile + smoke |
| T4 | UI avatar + filme | web/src/components/*, services/api.ts | avatar anima falando; botão→status→player |
| T5 | Avatar img (codex) | web/public/avatar.png | loira entrevistadora, busto, fundo neutro |
| T6 | Deploy demo-hermes | scripts, VM | web+server systemd, funnel :443 público |
| T7 | Vercel proxy+DNS | vercel project | storyteller.jazzautomations.com.br responde 200 |
| T8 | E2E | — | conversa→filme→vídeo na URL pública |
