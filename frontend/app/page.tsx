"use client";
import { useState, useRef, useEffect, FormEvent } from "react";
import ReactMarkdown from "react-markdown";

type Message = {
  role: "user" | "assistant";
  content: string;
  fontes?: string[];
  votado?: "util" | "nao_util";
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_URL = `${API_BASE}/api/v1/chat/stream`;
const FEEDBACK_URL = `${API_BASE}/api/v1/feedback`;
const SESSION_KEY = "cacic-session-id";

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

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [falhou, setFalhou] = useState(false);
  const [limiteAtingido, setLimiteAtingido] = useState(false);
  const ultimaPerguntaRef = useRef<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const sessionIdRef = useRef<string>("");

  useEffect(() => {
    sessionIdRef.current = obterSessionId();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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
    const userMsg: Message = { role: "user", content: texto };
    ultimaPerguntaRef.current = texto;
    setMessages((prev) => [...prev, userMsg, { role: "assistant", content: "" }]);
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

  const sendMessage = (e: FormEvent) => {
    e.preventDefault();
    const texto = input.trim();
    if (!texto || isLoading) return;
    setInput("");
    void enviar(texto);
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

  return (
    <main className="flex min-h-screen flex-col items-center bg-page p-4">
      <div className="w-full max-w-3xl bg-surface rounded-xl shadow-lg overflow-hidden flex flex-col h-[90vh]">
        {/* Cabeçalho */}
        <div className="bg-primary p-4 text-primary-ink flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold">Assistente Institucional CACIC</h1>
            <p className="text-sm text-primary-ink/70">
              Universidade Estadual de Santa Cruz (UESC)
            </p>
          </div>
          <button
            type="button"
            onClick={novaConversa}
            disabled={isLoading || messages.length === 0}
            className="text-sm border border-primary-ink/30 rounded-lg px-3 py-1 hover:bg-primary-ink/10 disabled:opacity-50 transition-colors"
          >
            Nova conversa
          </button>
        </div>

        {/* Área de Mensagens */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-ink-faint mt-10">
              Faça uma pergunta sobre o regulamento, horas de ACC ou TCC!
            </div>
          )}

          {messages.map((msg, index) => {
            const streamingAgora = isLoading && index === messages.length - 1;
            const podeAvaliar =
              msg.role === "assistant" && msg.content.trim() !== "" && !streamingAgora;

            return (
              <div
                key={index}
                className={`flex flex-col ${
                  msg.role === "user" ? "items-end" : "items-start"
                }`}
              >
                <div
                  className={`max-w-[80%] rounded-lg p-3 ${
                    msg.role === "user"
                      ? "bg-primary text-primary-ink rounded-br-none whitespace-pre-wrap"
                      : "bg-surface-sunken text-ink rounded-bl-none border border-border"
                  }`}
                >
                  {msg.role === "assistant" ? (
                    <div className="resposta-markdown">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  ) : (
                    msg.content
                  )}
                </div>

                {msg.fontes && msg.fontes.length > 0 && (
                  <p className="mt-1 text-xs text-ink-faint px-1">
                    Fontes: {msg.fontes.join(", ")}
                  </p>
                )}

                {podeAvaliar && (
                  <div className="mt-1 flex items-center gap-2 px-1 text-xs text-ink-faint">
                    {msg.votado ? (
                      <span>Obrigado pelo retorno!</span>
                    ) : (
                      <>
                        <span>Essa resposta ajudou?</span>
                        <button
                          type="button"
                          onClick={() => enviarFeedback(index, true)}
                          aria-label="Útil"
                          className="hover:text-ink transition-colors"
                        >
                          👍
                        </button>
                        <button
                          type="button"
                          onClick={() => enviarFeedback(index, false)}
                          aria-label="Não útil"
                          className="hover:text-ink transition-colors"
                        >
                          👎
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>
            );
          })}
          {falhou && !isLoading && (
            <div className="flex justify-start">
              <button
                type="button"
                onClick={tentarNovamente}
                className="text-sm text-primary border border-border rounded-lg px-3 py-1 hover:bg-accent-soft transition-colors"
              >
                Tentar novamente
              </button>
            </div>
          )}
          {limiteAtingido && !isLoading && (
            <div className="flex justify-start">
              <button
                type="button"
                onClick={novaConversa}
                className="text-sm text-primary border border-border rounded-lg px-3 py-1 hover:bg-accent-soft transition-colors"
              >
                Nova conversa
              </button>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Barra de Digitação */}
        <form onSubmit={sendMessage} className="p-4 bg-surface-sunken border-t border-border flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Digite sua dúvida acadêmica..."
            maxLength={2000}
            className="flex-1 border border-border bg-surface rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary text-ink"
            disabled={isLoading || limiteAtingido}
          />
          <button
            type="submit"
            disabled={isLoading || limiteAtingido || !input.trim()}
            className="bg-primary text-primary-ink px-6 py-2 rounded-lg font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            Enviar
          </button>
        </form>
      </div>
    </main>
  );
}
