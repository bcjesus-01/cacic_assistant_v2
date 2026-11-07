import React from 'react';

// Tipagem rigorosa com TypeScript
interface MessageProps {
  content: string;
  role: 'user' | 'assistant';
}

export const MessageBubble: React.FC<MessageProps> = ({ content, role }) => {
  const isUser = role === 'user';

  return (
    <div className={`flex w-full mb-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div 
        className={`max-w-[75%] px-5 py-3 rounded-2xl shadow-sm text-sm md:text-base leading-relaxed
          ${isUser 
            // Cores do Estudante: Fundo azul, texto branco
            ? 'bg-blue-600 text-white rounded-tr-none' 
            // Cores do CACIC/Bot: Fundo cinza claro (Dark Mode: fundo escuro)
            : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200 rounded-tl-none border dark:border-gray-700'
          }`}
      >
        {/* Renderiza o texto suportando quebras de linha */}
        <p className="whitespace-pre-wrap">{content}</p>
      </div>
    </div>
  );
};
