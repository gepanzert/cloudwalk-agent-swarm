"use client"

import { ExampleQuery } from "@/lib/types"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { MessageSquare, RotateCcw, ChevronRight } from "lucide-react"
import { ThemeToggle } from "./theme-toggle"

const exampleQueries: ExampleQuery[] = [
  { text: "What are the fees of the Maquininha Smart?" },
  { text: "Why am I not able to make transfers?", userId: "user_limit_reached" },
  { text: "I can't sign in to my account.", userId: "user_login_issue" },
  { text: "Quando foi o último jogo do Palmeiras?" }
]

interface ChatSidebarProps {
  onSelectQuery: (query: ExampleQuery) => void
  onClearChat: () => void
  messageCount: number
}

export function ChatSidebar({ onSelectQuery, onClearChat, messageCount }: ChatSidebarProps) {
  return (
    <aside className="w-80 border-r border-border bg-sidebar flex flex-col h-full">
      <div className="p-4 border-b border-sidebar-border">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <MessageSquare className="h-4 w-4 text-primary-foreground" />
            </div>
            <div>
              <h1 className="font-semibold text-sidebar-foreground text-sm">InfinitePay</h1>
              <p className="text-[10px] text-sidebar-foreground/60">Agent Swarm</p>
            </div>
          </div>
          <ThemeToggle />
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4">
        <div className="mb-4">
          <h2 className="text-xs font-medium text-sidebar-foreground/60 uppercase tracking-wider mb-3">
            Exemplos de Consultas
          </h2>
          <div className="space-y-2">
            {exampleQueries.map((query, index) => (
              <Card
                key={index}
                className="p-3 cursor-pointer hover:bg-sidebar-accent transition-colors border-sidebar-border group"
                onClick={() => onSelectQuery(query)}
              >
                <div className="flex items-start gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-sidebar-foreground leading-snug line-clamp-2">
                      {query.text}
                    </p>
                    {query.userId && (
                      <p className="text-[10px] text-sidebar-foreground/50 mt-1 font-mono">
                        user_id: {query.userId}
                      </p>
                    )}
                  </div>
                  <ChevronRight className="h-4 w-4 text-sidebar-foreground/30 group-hover:text-primary shrink-0 mt-0.5 transition-colors" />
                </div>
              </Card>
            ))}
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-sidebar-border">
        <Button
          variant="outline"
          className="w-full justify-center gap-2 text-sidebar-foreground border-sidebar-border hover:bg-sidebar-accent"
          onClick={onClearChat}
          disabled={messageCount === 0}
        >
          <RotateCcw className="h-4 w-4" />
          Nova Conversa
        </Button>
      </div>
    </aside>
  )
}
