"use client";
import { useState, useRef, useEffect, FormEvent } from "react";

type Message = { role: "user" | "assistant"; content: string };

const API_URL = `${
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
}/api/v1/chat/stream`;
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

    const updateAssistant = (text: string) =>
      setMessages((prev) => {
        const copy = [...prev];
        copy[copy.length - 1] = { ...copy[copy.length - 1], content: text };
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
      const stream = { texto: "", finished: false, erro: "", limite: false };

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
        updateAssistant(stream.texto);
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

  return (
    <main className="flex min-h-screen flex-col items-center bg-gray-50 p-4">
      <div className="w-full max-w-3xl bg-white rounded-xl shadow-lg overflow-hidden flex flex-col h-[90vh]">
        {/* Cabeçalho */}
        <div className="bg-blue-800 p-4 text-white flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold">Assistente Institucional CACIC</h1>
            <p className="text-sm text-blue-200">
              Universidade Estadual de Santa Cruz (UESC)
            </p>
          </div>
          <button
            type="button"
            onClick={novaConversa}
            disabled={isLoading || messages.length === 0}
            className="text-sm border border-blue-300 rounded-lg px-3 py-1 hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            Nova conversa
          </button>
        </div>

        {/* Área de Mensagens */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-gray-400 mt-10">
              Faça uma pergunta sobre o regulamento, horas de ACC ou TCC!
            </div>
          )}

          {messages.map((msg, index) => (
            <div
              key={index}
              className={`flex ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[80%] rounded-lg p-3 whitespace-pre-wrap ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white rounded-br-none"
                    : "bg-gray-100 text-gray-800 rounded-bl-none border border-gray-200"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}
          {falhou && !isLoading && (
            <div className="flex justify-start">
              <button
                type="button"
                onClick={tentarNovamente}
                className="text-sm text-blue-800 border border-blue-300 rounded-lg px-3 py-1 hover:bg-blue-50 transition-colors"
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
                className="text-sm text-blue-800 border border-blue-300 rounded-lg px-3 py-1 hover:bg-blue-50 transition-colors"
              >
                Nova conversa
              </button>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Barra de Digitação */}
        <form onSubmit={sendMessage} className="p-4 bg-gray-50 border-t flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Digite sua dúvida acadêmica..."
            maxLength={2000}
            className="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-black"
            disabled={isLoading || limiteAtingido}
          />
          <button
            type="submit"
            disabled={isLoading || limiteAtingido || !input.trim()}
            className="bg-blue-800 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            Enviar
          </button>
        </form>
      </div>
    </main>
  );
}
