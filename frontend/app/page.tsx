"use client";
import { useState, useRef, useEffect, FormEvent, KeyboardEvent } from "react";
import ReactMarkdown from "react-markdown";

type Message = {
  role: "user" | "assistant";
  content: string;
  hora: string;
  fontes?: string[];
  votado?: "util" | "nao_util";
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_URL = `${API_BASE}/api/v1/chat/stream`;
const FEEDBACK_URL = `${API_BASE}/api/v1/feedback`;
const SESSION_KEY = "cacic-session-id";

// Temas reais do FAQ/avaliação do projeto — não placeholder (ver design/README.md).
const TOPICOS = [
  {
    titulo: "Horas complementares",
    texto: "Quantas horas preciso e como comprovar.",
    pergunta: "Quantas horas complementares eu preciso para me formar?",
  },
  {
    titulo: "Trancamento de matrícula",
    texto: "Prazos, limite de semestres e como pedir.",
    pergunta: "O que é o trancamento total de matrícula?",
  },
  {
    titulo: "Estágio e TCC",
    texto: "Se são a mesma coisa e qual a carga horária.",
    pergunta: "O TCC e o estágio são a mesma coisa?",
  },
  {
    titulo: "Mais Futuro",
    texto: "Quem pode receber o auxílio permanência.",
    pergunta: "Quem pode receber o Mais Futuro?",
  },
];

const SUGESTOES = TOPICOS.map((t) => t.pergunta);

// crypto.randomUUID só existe em contexto seguro (https ou localhost); há um plano B.
function novoId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}

// Um identificador por navegador: cada aluno tem o próprio histórico de conversa.
function obterSessionId(): string {
  try {
    const salvo = window.localStorage.getItem(SESSION_KEY);
    if (salvo) return salvo;
    const novo = novoId();
    window.localStorage.setItem(SESSION_KEY, novo);
    return novo;
  } catch {
    return novoId(); // localStorage indisponível (modo privado, por exemplo)
  }
}

function horaAgora(): string {
  return new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

// Avatar hexagonal: um por bloco de mensagem do assistente (design/components/Brand/README.md).
function AvatarAssistente() {
  return (
    <svg className="cacic-avatar" viewBox="0 0 36 40" aria-hidden="true">
      <path
        d="M18 2.5 33.15 11.25v17.5L18 37.5 2.85 28.75v-17.5z"
        fill="none"
        stroke="url(#cacic-hex)"
        strokeWidth="3"
        strokeLinejoin="round"
      />
      <path
        d="M18 12l6.9 4v8L18 28l-6.9-4v-8z"
        fill="var(--yellow)"
        stroke="var(--yellow)"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function IconeHexagono() {
  return (
    <svg className="cacic-topic__hex" viewBox="0 0 36 40" aria-hidden="true">
      <path
        d="M18 2.5 33.15 11.25v17.5L18 37.5 2.85 28.75v-17.5z"
        fill="none"
        stroke="url(#cacic-hex)"
        strokeWidth="3"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [falhou, setFalhou] = useState(false);
  const [limiteAtingido, setLimiteAtingido] = useState(false);
  const ultimaPerguntaRef = useRef<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const sessionIdRef = useRef<string>("");

  useEffect(() => {
    sessionIdRef.current = obterSessionId();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Campo de texto cresce com o conteúdo, até um limite (mesmo padrão do design).
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 144)}px`;
  }, [input]);

  const novaConversa = () => {
    if (isLoading) return;
    const novo = novoId();
    sessionIdRef.current = novo;
    try {
      window.localStorage.setItem(SESSION_KEY, novo);
    } catch {
      /* sem localStorage: o id vale só até recarregar a página */
    }
    setMessages([]);
    setFalhou(false);
    setLimiteAtingido(false);
  };

  const enviar = async (texto: string) => {
    const userMsg: Message = { role: "user", content: texto, hora: horaAgora() };
    ultimaPerguntaRef.current = texto;
    setMessages((prev) => [...prev, userMsg, { role: "assistant", content: "", hora: horaAgora() }]);
    setIsLoading(true);
    setFalhou(false);
    setLimiteAtingido(false);

    const updateAssistant = (text: string, extra?: Partial<Message>) =>
      setMessages((prev) => {
        const copy = [...prev];
        copy[copy.length - 1] = { ...copy[copy.length - 1], content: text, ...extra };
        return copy;
      });

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          thread_id: sessionIdRef.current || obterSessionId(),
          message: userMsg.content,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      // Estado do stream em um objeto: é alterado dentro de handleEvent e lido no laço.
      const stream = {
        texto: "",
        finished: false,
        erro: "",
        limite: false,
        fontes: [] as string[],
      };

      // Processa um evento SSE completo (bloco entre linhas em branco)
      const handleEvent = (rawEvent: string) => {
        let nomeEvento = "message";
        const linhasData: string[] = [];

        for (const line of rawEvent.split(/\r?\n/)) {
          if (line.startsWith("event:")) {
            nomeEvento = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            const valor = line.slice(5);
            linhasData.push(valor.startsWith(" ") ? valor.slice(1) : valor);
          }
        }
        if (linhasData.length === 0) return;

        const data = linhasData.join("\n");
        if (data === "[DONE]") {
          stream.finished = true;
          return;
        }

        let conteudo = data;
        try {
          const parsed = JSON.parse(data); // o backend envia cada token como string JSON
          if (typeof parsed === "string") conteudo = parsed;
        } catch {
          /* se não for JSON, usa o texto cru */
        }

        if (nomeEvento === "error") {
          stream.erro = conteudo;
        } else if (nomeEvento === "limite") {
          // Conversa longa demais: não adianta "tentar novamente", precisa de "nova conversa".
          stream.erro = conteudo;
          stream.limite = true;
        } else if (nomeEvento === "reset") {
          // O modelo de reserva assumiu: descarta o texto parcial e recomeça.
          stream.texto = "";
        } else if (nomeEvento === "fontes") {
          try {
            const parsedFontes = JSON.parse(data);
            if (Array.isArray(parsedFontes)) stream.fontes = parsedFontes;
          } catch {
            /* evento malformado: ignora, não afeta a resposta em si */
          }
        } else {
          stream.texto += conteudo;
        }
      };

      while (!stream.finished) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Só processa eventos completos; o resto fica no buffer
        const events = buffer.split(/\r?\n\r?\n/);
        buffer = events.pop() ?? "";

        for (const ev of events) {
          handleEvent(ev);
          if (stream.finished) break;
        }

        updateAssistant(stream.texto);
      }

      // Descarrega o que sobrou no decoder/buffer
      buffer += decoder.decode();
      if (!stream.finished && buffer.trim()) handleEvent(buffer);

      if (stream.erro) {
        updateAssistant(
          stream.texto ? `${stream.texto}\n\n${stream.erro}` : stream.erro
        );
        if (stream.limite) {
          setLimiteAtingido(true);
        } else {
          setFalhou(true);
        }
      } else if (!stream.texto) {
        updateAssistant("Não recebi resposta do servidor. Tente novamente.");
        setFalhou(true);
      } else {
        updateAssistant(stream.texto, { fontes: stream.fontes });
      }
    } catch (error) {
      console.error("Erro no chat:", error);
      updateAssistant("Erro de conexão com o servidor. Verifique o backend.");
      setFalhou(true);
    } finally {
      setIsLoading(false);
    }
  };

  const enviarPergunta = () => {
    const texto = input.trim();
    if (!texto || isLoading || limiteAtingido) return;
    setInput("");
    void enviar(texto);
  };

  const sendMessage = (e: FormEvent) => {
    e.preventDefault();
    enviarPergunta();
  };

  const aoPressionarTecla = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      enviarPergunta();
    }
  };

  const preencherSugestao = (texto: string) => {
    if (isLoading || limiteAtingido) return;
    setInput(texto);
    textareaRef.current?.focus();
  };

  // Reenvia a última pergunta. A tentativa que falhou sai da tela; o histórico do servidor
  // pode manter a pergunta repetida, o que não afeta a resposta.
  const tentarNovamente = () => {
    if (isLoading || !ultimaPerguntaRef.current) return;
    setMessages((prev) => prev.slice(0, -2));
    void enviar(ultimaPerguntaRef.current);
  };

  // Útil/não útil: a pergunta correspondente é sempre a mensagem anterior do usuário.
  const enviarFeedback = async (index: number, util: boolean) => {
    const resposta = messages[index];
    const perguntaMsg = messages[index - 1];
    if (!perguntaMsg || perguntaMsg.role !== "user" || resposta.votado) return;

    setMessages((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], votado: util ? "util" : "nao_util" };
      return copy;
    });

    try {
      await fetch(FEEDBACK_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          thread_id: sessionIdRef.current || obterSessionId(),
          pergunta: perguntaMsg.content,
          resposta: resposta.content,
          util,
        }),
      });
    } catch (error) {
      console.error("Erro ao enviar feedback:", error);
    }
  };

  const copiarResposta = (texto: string) => {
    navigator.clipboard?.writeText(texto).catch(() => {
      /* sem permissão de clipboard: não quebra a UI */
    });
  };

  const emConversa = messages.length > 0;

  return (
    <>
      {/* Gradiente usado pelo contorno do avatar/hexágonos dos tópicos — declarado uma vez só. */}
      <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true" focusable="false">
        <defs>
          <linearGradient id="cacic-hex" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="var(--coral)" />
            <stop offset="0.55" stopColor="var(--magenta)" />
            <stop offset="1" stopColor="var(--violet)" />
          </linearGradient>
        </defs>
      </svg>

      <div className="cacic-page">
        <header className="cacic-header">
          <div className="cacic-header__id">
            <img className="cacic-logo" src="/cacic-logo.svg" alt="CACIC" />
          </div>
          <span className="cacic-handle">@cacicuesc</span>
          <span className="cacic-dots" aria-hidden="true"></span>
          <span className="cacic-status">Online</span>
          <button
            type="button"
            className="cacic-btn"
            onClick={novaConversa}
            disabled={isLoading || messages.length === 0}
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 5v14M5 12h14" />
            </svg>
            Nova conversa
          </button>
        </header>

        {!emConversa ? (
          <main className="cacic-thread" style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
            <div className="cacic-hero" style={{ paddingTop: 0 }}>
              <span className="cacic-pill">Assistente virtual do CACIC</span>
              <h1 className="cacic-hero__title">
                Tire suas dúvidas
                <br />
                sobre o <span className="cacic-grad">regimento</span>
                <br />
                da UESC
              </h1>
              <p className="cacic-hero__lead">
                Pergunte em linguagem simples. As respostas vêm com a fonte, para você conferir
                no documento oficial.
              </p>
              <div className="cacic-topics">
                {TOPICOS.map((t) => (
                  <button
                    key={t.titulo}
                    type="button"
                    className="cacic-topic"
                    onClick={() => !isLoading && enviar(t.pergunta)}
                  >
                    <IconeHexagono />
                    <span className="cacic-topic__body">
                      <span className="cacic-topic__title">{t.titulo}</span>
                      <span className="cacic-topic__text">{t.texto}</span>
                    </span>
                    <svg className="cacic-topic__go" viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M5 12h14M13 6l6 6-6 6" />
                    </svg>
                  </button>
                ))}
              </div>
            </div>
          </main>
        ) : (
          <main className="cacic-thread">
            <div className="cacic-thread__inner">
              <div className="cacic-day">Hoje</div>

              {messages.map((msg, index) => {
                if (msg.role === "user") {
                  return (
                    <div key={index} className="cacic-msg cacic-msg--user">
                      <div className="cacic-msg__body">
                        <span className="cacic-msg__meta">Você · {msg.hora}</span>
                        <div className="cacic-bubble cacic-bubble--user">
                          <p>{msg.content}</p>
                        </div>
                      </div>
                    </div>
                  );
                }

                const streamingVazio =
                  isLoading && index === messages.length - 1 && msg.content.trim() === "";
                const comErro =
                  (falhou || limiteAtingido) && index === messages.length - 1 && !isLoading;
                const podeAvaliar = !streamingVazio && !comErro && msg.content.trim() !== "";

                return (
                  <div key={index} className="cacic-msg">
                    <AvatarAssistente />
                    <div className="cacic-msg__body">
                      {streamingVazio ? (
                        <div className="cacic-typing" role="status" aria-label="Assistente digitando">
                          <span></span>
                          <span></span>
                          <span></span>
                        </div>
                      ) : (
                        <>
                          <span className="cacic-msg__meta">Assistente CACIC · {msg.hora}</span>
                          <div className={`cacic-bubble${comErro ? " cacic-bubble--error" : ""}`}>
                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                          </div>

                          {!comErro && msg.fontes && msg.fontes.length > 0 && (
                            <div className="cacic-sources">
                              <span className="cacic-sources__label">Fonte</span>
                              {msg.fontes.map((fonte) => (
                                <span key={fonte} className="cacic-source">
                                  <svg viewBox="0 0 24 24" aria-hidden="true">
                                    <path d="M7 3h7l5 5v13H7z" />
                                    <path d="M14 3v5h5" />
                                  </svg>
                                  {fonte}
                                </span>
                              ))}
                            </div>
                          )}

                          {comErro && (
                            <div>
                              <button type="button" className="cacic-btn" onClick={limiteAtingido ? novaConversa : tentarNovamente}>
                                <svg viewBox="0 0 24 24" aria-hidden="true">
                                  <path d="M20 11a8 8 0 1 0-2.3 5.7" />
                                  <path d="M20 5v6h-6" />
                                </svg>
                                {limiteAtingido ? "Nova conversa" : "Tentar de novo"}
                              </button>
                            </div>
                          )}

                          {podeAvaliar && (
                            <div className="cacic-actions">
                              <button
                                type="button"
                                className="cacic-icon-btn"
                                aria-label="Copiar resposta"
                                onClick={() => copiarResposta(msg.content)}
                              >
                                <svg viewBox="0 0 24 24" aria-hidden="true">
                                  <rect x="9" y="9" width="11" height="11" rx="2.5" />
                                  <path d="M5 15V6.5A2.5 2.5 0 0 1 7.5 4H15" />
                                </svg>
                              </button>
                              <button
                                type="button"
                                className="cacic-icon-btn"
                                aria-label="Resposta útil"
                                disabled={!!msg.votado}
                                onClick={() => enviarFeedback(index, true)}
                                style={{
                                  opacity: msg.votado && msg.votado !== "util" ? 0.35 : 1,
                                  color: msg.votado === "util" ? "var(--ok)" : undefined,
                                }}
                              >
                                <svg viewBox="0 0 24 24" aria-hidden="true">
                                  <path d="M7 11v9H4v-9zM7 11l4-7c1.7 0 2.5 1.2 2.2 2.8L12.8 9H19a2 2 0 0 1 2 2.3l-1.2 6.5A2 2 0 0 1 17.8 19H7" />
                                </svg>
                              </button>
                              <button
                                type="button"
                                className="cacic-icon-btn"
                                aria-label="Resposta não ajudou"
                                disabled={!!msg.votado}
                                onClick={() => enviarFeedback(index, false)}
                                style={{
                                  opacity: msg.votado && msg.votado !== "nao_util" ? 0.35 : 1,
                                  color: msg.votado === "nao_util" ? "var(--danger)" : undefined,
                                }}
                              >
                                <svg className="flip" viewBox="0 0 24 24" aria-hidden="true">
                                  <path d="M7 11v9H4v-9zM7 11l4-7c1.7 0 2.5 1.2 2.2 2.8L12.8 9H19a2 2 0 0 1 2 2.3l-1.2 6.5A2 2 0 0 1 17.8 19H7" />
                                </svg>
                              </button>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>
          </main>
        )}

        <div className="cacic-dock">
          <div className="cacic-dock__inner">
            {emConversa && (
              <div className="cacic-chips" role="list">
                {SUGESTOES.map((s) => (
                  <button
                    key={s}
                    type="button"
                    role="listitem"
                    className="cacic-chip"
                    onClick={() => preencherSugestao(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
            <form onSubmit={sendMessage} className={`cacic-composer${isLoading ? " cacic-composer--busy" : ""}`}>
              <textarea
                ref={textareaRef}
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={aoPressionarTecla}
                placeholder="Pergunte sobre matrícula, faltas, trancamento…"
                maxLength={2000}
                aria-label="Sua pergunta"
                disabled={isLoading || limiteAtingido}
              />
              <button type="submit" className="cacic-send" aria-label="Enviar pergunta" disabled={isLoading || limiteAtingido || !input.trim()}>
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M6 6l6 6-6 6M13 6l6 6-6 6" />
                </svg>
              </button>
            </form>
            <p className="cacic-note">O assistente pode errar. Confirme sempre no texto oficial do regimento.</p>
          </div>
        </div>
      </div>
    </>
  );
}
