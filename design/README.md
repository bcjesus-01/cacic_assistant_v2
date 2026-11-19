Este sistema desenha o **assistente virtual do CACIC**, o chat que ajuda os alunos da UESC com dúvidas regimentares. A identidade vem do logo do Centro Acadêmico de Computação e das artes de divulgação da Sinform: fundo grafite quadriculado, índigo e amarelo do logo, títulos pesados em caixa alta e um gradiente coral → violeta usado com economia.

## Voz e conteúdo

- Fale com o aluno de **você**, em frases curtas e diretas, como o CACIC fala nas redes: "Confira os minicursos do segundo dia da Sinform 2026".
- Escreva o título de abertura em CAIXA ALTA (`display`). Todo o resto, inclusive botões e chips, em caixa de frase: "Nova conversa", "Como trancar a matrícula?".
- Sem emoji. O assistente é simpático, mas trata de regras da universidade; a clareza vem antes do tom.
- Em toda resposta: primeiro a resposta direta, depois o contexto, por último a fonte no chip `cacic-source` ("Regimento Geral da UESC · art. 00").
- Nunca invente artigo, prazo, percentual ou nome de documento. Sem fonte, diga que não encontrou e indique o colegiado do curso ou a secretaria.
- O aviso "O assistente pode errar. Confirme sempre no texto oficial do regimento." fica sempre sob o campo de mensagem (`cacic-note`).
- Os textos das telas deste sistema são de exemplo; troque artigos e conteúdo pelas respostas reais.

## Fundamentos visuais

**Cor.** O tema padrão é `dark`: fundo `bg` (#191a1a) com a grade `bg-grid` a cada `space-6` (32px), como nas artes. `light` é o tema alternativo, com os mesmos papéis.
- Texto principal em `ink`, secundário em `ink-muted`, links e chips de fonte em `link`.
- `indigo` é preenchimento: balão do aluno e base do botão de enviar, sempre com `on-indigo`. Nunca o use como texto ou borda sobre `bg` (2,6:1); para texto use `link`.
- `yellow` é o destaque do logo: hexágono do avatar, anel de foco no tema escuro. No tema claro só como preenchimento com `on-yellow`.
- Superfícies: `surface` (campo, chips, cards) e `surface-raised` (balão do assistente). Bordas de controle em `line-strong`; fios decorativos em `line`.
- Status sempre com palavra ou ícone: `ok` ("Online"), `danger` (erro).

**Gradientes.** Dois, vindos das artes, e no máximo dois usos por tela.
- `--gradient-accent` (`coral` → `magenta` → `violet`) em UMA palavra do título, com a classe `cacic-grad`. Só em texto de 24px ou mais.
- `--gradient-pill` (`indigo-deep` → `magenta`) na pílula `cacic-pill` e no botão primário, com `on-indigo`, como o rodapé "24ª Semana de Informática da UESC".
- `--gradient-send` (`violet` → `indigo`) no botão de enviar.

**Tipografia.** Poppins em tudo (`--font-sans`): 800 nos títulos `display`, 700/600 em `title` e `subtitle`, 400 no texto. Os rótulos (`label`) vão em caixa alta com espaçamento largo de 0,16em, como o handle "@CACICUESC" e o rodapé das artes. Texto de balão em 15px/24px.

**Forma.** O hexágono é o motivo: o logo é um favo. O avatar do assistente é um hexágono de contorno em gradiente com um hexágono `yellow` no centro; os cards de tópico usam o contorno vazio. Balões usam `radius-lg` com o canto do falante em 6px; chips, campo de mensagem, botões e pílulas usam `radius-pill`; cards, `radius-md`.

**Linha pontilhada.** O handle do cabeçalho e o divisor de dia terminam em um pontilhado de 2px em `line-strong` (`cacic-dots`), herdado da arte da Sinform.

**Espaçamento.** Base de 8px: 12px entre avatar e balão, 24px entre mensagens, 32px de margem lateral no desktop e 16px no celular. A coluna de conversa nunca passa de 760px.

**Foco.** Anel sólido de 2px em `focus` com 2px de folga na cor da página, em todo controle. O campo de mensagem mostra o anel no contêiner inteiro.

**Movimento.** Só o indicador de digitação anima; ele para com `prefers-reduced-motion`.

## Iconografia

- Ícones de traço de 1,75px, cantos arredondados, 18px nos botões e 14px nos chips, desenhados com `currentColor` para herdar a cor do texto.
- O botão de enviar usa o duplo chevron "»" da arte, em traço de 2,25px.
- Sem emoji e sem ícones preenchidos, exceto o hexágono amarelo do avatar.

## Logo

Use `assets/Logos/cacic-logo.svg` sempre por `<img>`, sobre `bg` escuro, com altura mínima de 40px (52px no cabeçalho desktop). Não recolora, não distorça e não desenhe uma versão nova. Sobre fundo claro o amarelo perde contraste: reserve esse uso a peças grandes.

## Estrutura do chat

A página é uma coluna: `cacic-header` (logo, handle, pontilhado, status "Online", "Nova conversa"), `cacic-thread` (a conversa, ancorada embaixo) e `cacic-dock` (chips, campo de mensagem e aviso).
- **Tela inicial:** pílula, título `display` com uma palavra em `cacic-grad`, frase de apoio em `ink-muted` e quatro `cacic-topic`. Sem chips.
- **Conversa:** divisor `cacic-day`, mensagens `cacic-msg`, chips de pergunta acima do campo.
- **Resposta do assistente:** meta em `label`, balão, chip de fonte, ações (copiar, útil, não ajudou).
- **Digitando:** `cacic-typing` no lugar da resposta. **Erro:** balão com borda `danger`, ícone, frase e "Tentar de novo".
- **Enviando:** campo esmaecido e botão de enviar desativado. Botão desativado também quando o campo está vazio.
- **Celular (até 640px):** esconda handle e pontilhado, use `display-sm`, uma coluna de tópicos e margens de 16px; os chips rolam na horizontal.

## Usar em código

Carregue `tokens.css`, depois `components/bundle.css`, e a Poppins (400 a 800). O HTML de cada peça está no `preview.html` do componente; as classes `cacic-*` não dependem de framework. Defina o tema com `data-theme="dark"` ou `data-theme="light"` no elemento `html`.
