"use client"

import { useEffect, useRef, useState } from "react"
import { ChatMessage } from "./chat-message"
import { ChatInput } from "./chat-input"
import { ChatSidebar } from "./chat-sidebar"
import { LoadingIndicator } from "./loading-indicator"
import { useChat } from "@/hooks/use-chat"
import { ExampleQuery } from "@/lib/types"
import { Bot, Menu } from "lucide-react"
import { Button } from "@/components/ui/button"

export function ChatInterface() {
  const { conversation, sendMessage, clearConversation } = useChat()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [pendingQuery, setPendingQuery] = useState<string>("")
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [conversation.messages, conversation.isLoading])

  const handleSelectQuery = (query: ExampleQuery) => {
    setPendingQuery(query.text)
    setSidebarOpen(false)
  }

  const handleSend = (message: string) => {
    setPendingQuery("")
    sendMessage(message)
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        fixed inset-y-0 left-0 z-50 lg:relative lg:z-auto
        transform transition-transform duration-200 ease-in-out
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <ChatSidebar
          onSelectQuery={handleSelectQuery}
          onClearChat={clearConversation}
          messageCount={conversation.messages.length}
        />
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <header className="flex-shrink-0 flex items-center gap-3 px-4 py-3 border-b border-border bg-background h-[57px]">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden h-9 w-9"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-5 w-5" />
            <span className="sr-only">Abrir menu</span>
          </Button>

          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
              <Bot className="h-4 w-4 text-primary" />
            </div>
            <div>
              <h2 className="font-medium text-sm text-foreground">InfinitePay Agent Swarm</h2>
              <p className="text-[10px] text-muted-foreground">Suporte inteligente 24/7</p>
            </div>
          </div>

          <div className="ml-auto flex items-center gap-2">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-xs text-muted-foreground">Online</span>
            </span>
          </div>
        </header>

        {/* Messages area — scrolls independently */}
        <div className="flex-1 overflow-y-auto">
          <div className="py-4 space-y-4">
            {conversation.messages.length === 0 && (
              <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
                <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
                  <Bot className="h-8 w-8 text-primary" />
                </div>
                <h3 className="font-semibold text-lg text-foreground mb-2">
                  Bem-vindo ao InfinitePay Agent Swarm
                </h3>
                <p className="text-muted-foreground text-sm max-w-md leading-relaxed">
                  Sou seu assistente virtual inteligente. Posso ajudar com dúvidas sobre taxas,
                  problemas com transações, suporte técnico e muito mais. Como posso ajudar?
                </p>
              </div>
            )}

            {conversation.messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}

            {conversation.isLoading && <LoadingIndicator />}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Thread ID */}
        {conversation.threadId && (
          <div className="flex-shrink-0 px-4 py-1 border-t border-border bg-muted/30">
            <p className="text-[10px] text-muted-foreground font-mono text-center">
              thread_id: {conversation.threadId}
            </p>
          </div>
        )}

        {/* Input */}
        <div className="flex-shrink-0">
          <ChatInput
            onSend={handleSend}
            disabled={conversation.isLoading}
            initialValue={pendingQuery}
            key={pendingQuery}
          />
        </div>
      </div>
    </div>
  )
}
