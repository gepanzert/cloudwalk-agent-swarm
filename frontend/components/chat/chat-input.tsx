"use client"

import { useState, FormEvent } from "react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Send } from "lucide-react"

interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
  initialValue?: string
}

export function ChatInput({ onSend, disabled, initialValue = "" }: ChatInputProps) {
  const [message, setMessage] = useState(initialValue)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (message.trim() && !disabled) {
      onSend(message.trim())
      setMessage("")
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 p-4 border-t border-border bg-background">
      <Input
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Digite sua mensagem..."
        disabled={disabled}
        className="flex-1 bg-muted/50 border-border focus-visible:ring-primary"
      />
      <Button 
        type="submit" 
        disabled={disabled || !message.trim()}
        className="bg-primary hover:bg-primary/90 text-primary-foreground px-4"
      >
        <Send className="h-4 w-4" />
        <span className="sr-only">Enviar mensagem</span>
      </Button>
    </form>
  )
}
