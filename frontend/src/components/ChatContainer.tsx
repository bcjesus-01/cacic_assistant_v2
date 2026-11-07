'use client'; // Diretiva do Next.js para rodar no navegador, permitindo hooks como useState

import React, { useState, useRef } from 'react';
import { MessageBubble } from './MessageBubble';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

export const ChatContainer: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null); // Referência para rolar a tela

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = { id: Date.now().toString(), role: 'user', content: inputValue };
    const placeholderId = (Date.now() + 1).toString();
    
    // Adiciona a pergunta do usuário e um balão vazio para o Bot
    setMessages(prev => [...prev, userMessage, { id: placeholderId, role: 'assistant', content: '' }]);
    setInputValue('');
    setIsLoading(true);

    try {
      // Faz o POST para o nosso FastAPI
      const response = await fetch('http://localhost:8000/api/v1/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pergunta: userMessage.content, session_id: 'sessao_estudante_1' }),
      });

      if (!response.body) throw new Error("Body da resposta não encontrado.");

      // A MÁGICA DO STREAMING: Lemos a resposta como um fluxo de bytes
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // Decodifica o pedaço (chunk) e processa o texto SSE (formato: "data: ...\n\n")
        const chunkStr = decoder.decode(value, { stream: true });
        
        // Remove a marcação 'data: ' do SSE para pegar só a string pura
        const lines = chunkStr.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[FIM_DA_TRANSMISSAO]') break;
            
            // Injeta o caractere instantaneamente no estado do React
            setMessages(prev => prev.map(msg => 
              msg.id === placeholderId ? { ...msg, content: msg.content + data } : msg
            ));
            
            // Rola a tela para baixo suavemente
            bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
          }
        }
      }
    } catch (error) {
      console.error("Erro na comunicação com a API:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto bg-white dark:bg-gray-900 transition-colors">
      <header className="p-4 border-b dark:border-gray-800 text-center">
        <h1 className="text-xl font-bold dark:text-white">Assistente Virtual CACIC</h1>
      </header>

      {/* Área das Mensagens (Scroll) */}
      <main className="flex-1 overflow-y-auto p-4 sm:p-6">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} role={msg.role} content={msg.content} />
        ))}
        <div ref={bottomRef} />
      </main>

      {/* Caixa de Entrada com Acessibilidade (aria-label) */}
      <footer className="p-4 border-t dark:border-gray-800">
        <form onSubmit={handleSendMessage} className="flex gap-2 relative">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={isLoading}
            aria-label="Digite sua pergunta para o assistente"
            placeholder="Pergunte sobre ACCs, TCC, horários..."
            className="flex-1 p-3 border rounded-xl bg-gray-50 dark:bg-gray-800 dark:border-gray-700 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none transition-all disabled:opacity-50"
          />
          <button 
            type="submit" 
            disabled={isLoading || !inputValue.trim()}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl transition-all disabled:opacity-50"
          >
            Enviar
          </button>
        </form>
      </footer>
    </div>
  );
};
