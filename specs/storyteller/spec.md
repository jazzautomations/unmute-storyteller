# Spec — Storyteller (UNMUTE hackathon)

## Problema
Todo mundo tem uma história que merecia ser filme — mas transformar memória em
cinema exige equipe. O Storyteller é uma entrevistadora AI (voz + avatar) que
ouve sua história com interesse genuíno, faz perguntas de acompanhamento e
transforma o resultado num curta-metragem via feita.ai.

## Golden path (o que aparece no demo de 2min)
1. Usuário abre storyteller.jazzautomations.com.br → "Começar conversa"
2. Nova (avatar loira) cumprimenta em pt-BR e entrevista: "me conta uma história
   que você adoraria ver virar filme" → perguntas curiosas sobre personagens,
   lugares, emoções, reviravoltas (1 pergunta por vez, reações naturais)
3. Usuário clica "Fazer meu filme" → transcript vai pro backend
4. Backend cria sessão feita → brief → feita produz shots → render
5. UI mostra progresso ("roteirizando…", "filmando…", "montando…") e toca o
   vídeo final na página

## Critérios de aceite
- [ ] Conversa por voz em pt-BR funciona ponta a ponta via Agora ConvoAI
      (agent entra no canal, fala, ouve, interrompe/recupera)
- [ ] Persona ouvinte ativo: ≥1 pergunta de acompanhamento por resposta do
      usuário, tom entusiasmado, coleta personagens/lugar/emoção/desfecho
- [ ] Avatar (imagem gerada) visível na tela de conversa com animação quando a
      agente fala
- [ ] POST /api/film aceita transcript → job id; GET /api/film/{id} retorna
      status progressivo; estado final expõe video_url que toca no browser
- [ ] App no ar em https://storyteller.jazzautomations.com.br (Vercel proxy →
      tailscale funnel → demo-hermes)

## Fora de escopo
Auth, multiusuário, edição do filme na UI, persistência, filmes >1min,
custom avatar vendors (heygen/anam — sem chaves), NSFW.

## Arquitetura
- web/ (Next.js): UI conversa + avatar + transcript (RTM) + botão filme + player
- server/ (FastAPI): token Agora + lifecycle do agent + pipeline de filme
  - POST /api/film {transcript} → feita session + brief → job
  - GET  /api/film/{job} → status {queued|producing|rendering|ready|error}
  - background poller: session events/desk → render → video asset URL
- feita.ai: sessão agent produz roteiro/shots/render (api.feita.ai/v1)
- Deploy: demo-hermes (web :3000, server :8000) + tailscale funnel :443 +
  Vercel rewrites storyteller.jazzautomations.com.br → funnel

## Premissas
- Transcript vem do cliente (RTM messageList) — não depender de history API
- Agente feita trabalha async; pipeline tolera minutos; UI faz polling 5s
- Repo público: SEM secrets — .env gitignored, FEITA_API_KEY placeholder only
