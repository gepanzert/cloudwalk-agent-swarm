import { Message } from "@/lib/types"
import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { AgentBadge, SentimentBadge } from "./agent-badge"
import { Bot, User } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

interface ChatMessageProps {
  message: Message
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user"

  return (
    <div
      className={cn(
        "flex gap-3 px-4",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      <Avatar className={cn(
        "h-8 w-8 shrink-0",
        isUser 
          ? "bg-blue-500 text-white" 
          : "bg-primary text-primary-foreground"
      )}>
        <AvatarFallback className={cn(
          isUser 
            ? "bg-blue-500 text-white" 
            : "bg-primary text-primary-foreground"
        )}>
          {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </AvatarFallback>
      </Avatar>

      <div className={cn(
        "flex flex-col gap-1.5 max-w-[75%]",
        isUser ? "items-end" : "items-start"
      )}>
        {!isUser && message.agentType && (
          <div className="flex items-center gap-2">
            <AgentBadge agentType={message.agentType} />
            {message.sentiment && <SentimentBadge sentiment={message.sentiment} />}
          </div>
        )}
        
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
            isUser
              ? "bg-blue-500 text-white rounded-br-md"
              : "bg-card text-card-foreground border border-border rounded-bl-md shadow-sm"
          )}
        >
          {isUser ? (
            <div className="whitespace-pre-wrap">{message.content}</div>
          ) : (
            <div className="markdown-content text-sm leading-relaxed">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        <span className="text-[10px] text-muted-foreground px-1">
          {message.timestamp.toLocaleTimeString("pt-BR", {
            hour: "2-digit",
            minute: "2-digit"
          })}
        </span>
      </div>
    </div>
  )
}
