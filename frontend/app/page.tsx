"use client";
import { useState, useRef, useEffect, FormEvent } from "react";

type Message = { role: "user" | "assistant"; content: string };

const API_URL = "http://localhost:8000/api/v1/chat/stream";

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg, { role: "assistant", content: "" }]);
    setInput("");
    setIsLoading(true);

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
          thread_id: "cacic-sessao-1",
          message: userMsg.content,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      let assistantResponse = "";
      let finished = false;

      // Processa um evento SSE completo (bloco entre linhas em branco)
      const handleEvent = (rawEvent: string) => {
        for (const line of rawEvent.split(/\r?\n/)) {
          if (!line.startsWith("data:")) continue;
          let data = line.slice(5);
          if (data.startsWith(" ")) data = data.slice(1);

          if (data === "[DONE]") {
            finished = true;
            return;
          }

          let token = data;
          try {
            token = JSON.parse(data); // backend envia cada token como JSON string
          } catch {
            /* se não for JSON, usa o texto cru */
          }

          assistantResponse += token;
        }
      };

      while (!finished) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Só processa eventos completos; o resto fica no buffer
        const events = buffer.split(/\r?\n\r?\n/);
        buffer = events.pop() ?? "";

        for (const ev of events) {
          handleEvent(ev);
          if (finished) break;
        }

        updateAssistant(assistantResponse);
      }

      // Descarrega o que sobrou no decoder/buffer
      buffer += decoder.decode();
      if (!finished && buffer.trim()) handleEvent(buffer);
      updateAssistant(assistantResponse);
    } catch (error) {
      console.error("Erro no chat:", error);
      updateAssistant("Erro de conexão com o servidor. Verifique o backend.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center bg-gray-50 p-4">
      <div className="w-full max-w-3xl bg-white rounded-xl shadow-lg overflow-hidden flex flex-col h-[90vh]">
        {/* Cabeçalho */}
        <div className="bg-blue-800 p-4 text-white">
          <h1 className="text-xl font-bold">Assistente Institucional CACIC</h1>
          <p className="text-sm text-blue-200">
            Universidade Estadual de Santa Cruz (UESC)
          </p>
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
          <div ref={messagesEndRef} />
        </div>

        {/* Barra de Digitação */}
        <form onSubmit={sendMessage} className="p-4 bg-gray-50 border-t flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Digite sua dúvida acadêmica..."
            className="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-black"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="bg-blue-800 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            Enviar
          </button>
        </form>
      </div>
    </main>
  );
}